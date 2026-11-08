"""Data layer for the Global Terrorism dashboard.

Everything in this module is plain pandas / numpy / scipy (no Streamlit), so every number the
dashboard shows can be re-derived and checked independently (see ``validate.py``).

Counting rules (identical to the notebook's engineered casualty features)
------------------------------------------------------------------------
* A casualty count is *valid* when it is present, non-negative and a whole number.
* Missing or invalid counts are never replaced with zero. Totals are sums over valid counts
  only and are always reported together with the share of incidents that reported a count.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy import stats

log = logging.getLogger("gtd")

APP_DIR = Path(__file__).resolve().parent
CSV_PATH = APP_DIR / "global_cleaned.csv"
PARQUET_PATH = APP_DIR / "data" / "gtd_cleaned.parquet"   # built from the CSV by scripts/build_data.py
PARQUET_META = PARQUET_PATH.with_suffix(".meta.json")

# The 30 analysis columns (the selection made in section 3 of the notebook).
BASE_COLUMNS = [
    "eventid", "iyear", "imonth", "iday",
    "country", "country_txt", "region", "region_txt", "provstate", "city", "latitude", "longitude",
    "attacktype1", "attacktype1_txt", "success", "suicide",
    "targtype1", "targtype1_txt", "targsubtype1_txt", "target1", "natlty1_txt",
    "weaptype1", "weaptype1_txt", "weapsubtype1_txt",
    "gname", "individual", "claimed",
    "nkill", "nwound", "property",
]
CATEGORY_COLUMNS = [
    "country_txt", "region_txt", "provstate", "city", "attacktype1_txt", "targtype1_txt",
    "targsubtype1_txt", "natlty1_txt", "weaptype1_txt", "weapsubtype1_txt", "gname",
]


class DataError(RuntimeError):
    """Raised when the dataset is missing or does not contain the expected columns."""


# --------------------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------------------
def valid_count(s: pd.Series) -> pd.Series:
    """Return the count where valid (present, >= 0, whole number); NaN otherwise."""
    s = pd.to_numeric(s, errors="coerce").astype("float64")
    ok = np.isfinite(s) & (s >= 0) & (np.mod(s, 1) == 0)
    return s.where(ok)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def data_path() -> Path:
    """Where the dataset is read from.

    ``GTD_DATA_PATH`` (CSV or Parquet) wins. Otherwise the bundled Parquet copy is used unless a
    ``global_cleaned.csv`` next to the app no longer matches the hash it was built from, in which case
    the CSV is read and a warning logged (rebuild with ``python scripts/build_data.py``).
    """
    env = os.environ.get("GTD_DATA_PATH")
    if env:
        return Path(env)
    if not PARQUET_PATH.exists():
        return CSV_PATH
    if CSV_PATH.exists():
        try:
            built_from = json.loads(PARQUET_META.read_text(encoding="utf-8"))["source_sha256"]
        except (OSError, ValueError, KeyError):
            built_from = None
        if built_from != sha256(CSV_PATH):
            log.warning("%s is stale (CSV changed); reading the CSV. Run scripts/build_data.py.", PARQUET_PATH.name)
            return CSV_PATH
    return PARQUET_PATH


def _columns_in(path: Path) -> list[str]:
    if path.suffix == ".parquet":
        return pq.read_schema(path).names
    return list(pd.read_csv(path, nrows=0).columns)


def read_raw(path: Path | str | None = None, columns: list[str] | None = None) -> pd.DataFrame:
    """The dataset exactly as stored (no derived columns, no dtype changes)."""
    path = Path(path) if path else data_path()
    if not path.exists():
        raise DataError(
            f"Dataset not found at '{path}'. Put global_cleaned.csv next to app.py and run "
            "'python scripts/build_data.py', or set the GTD_DATA_PATH environment variable."
        )
    if columns:
        missing = [c for c in columns if c not in _columns_in(path)]
        if missing:
            raise DataError(f"The dataset is missing required columns: {', '.join(missing)}")
    if path.suffix == ".parquet":
        return pd.read_parquet(path, columns=columns)
    return pd.read_csv(path, usecols=columns, low_memory=False)


def load_data(path: Path | str | None = None) -> pd.DataFrame:
    """Read the 30 analysis columns and append the derived helper columns.

    Source columns are never modified. Appended columns:
    ``nkill_v`` / ``nwound_v`` (valid counts), ``has_xy`` (valid coordinates) and ``group_named``
    (a perpetrator group other than Unknown is recorded).
    """
    df = read_raw(path, BASE_COLUMNS)[BASE_COLUMNS]
    for col in CATEGORY_COLUMNS:
        df[col] = df[col].astype("category")

    df["nkill_v"] = valid_count(df["nkill"])
    df["nwound_v"] = valid_count(df["nwound"])

    df["has_xy"] = df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    df["group_named"] = ~is_unknown(df["gname"])
    return df


def integrity_report(df: pd.DataFrame) -> dict:
    """Lightweight facts about the loaded data (shown in the README / validation)."""
    return {
        "rows": int(len(df)),
        "columns": len(BASE_COLUMNS),
        "year_min": int(df["iyear"].min()),
        "year_max": int(df["iyear"].max()),
        "unique_event_ids": bool(df["eventid"].is_unique),
        "fractional_nwound": int(((df["nwound"].notna()) & (df["nwound_v"].isna())).sum()),
        "fractional_nkill": int(((df["nkill"].notna()) & (df["nkill_v"].isna())).sum()),
    }


# --------------------------------------------------------------------------------------
# Selection (global filters)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    years: tuple[int, int]
    regions: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    attacks: tuple[str, ...] = ()
    targets: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()

    def n_active(self, full_years: tuple[int, int]) -> int:
        return (
            int(tuple(self.years) != tuple(full_years))
            + int(bool(self.regions)) + int(bool(self.countries)) + int(bool(self.groups))
            + int(bool(self.attacks)) + int(bool(self.targets))
        )

    def with_years(self, years: tuple[int, int]) -> Selection:
        return Selection(years=years, regions=self.regions, countries=self.countries, attacks=self.attacks,
                         targets=self.targets, groups=self.groups)


def _mask(df: pd.DataFrame, sel: Selection) -> pd.Series:
    mask = df["iyear"].between(sel.years[0], sel.years[1])
    if sel.regions:
        mask &= df["region_txt"].isin(sel.regions)
    if sel.countries:
        mask &= df["country_txt"].isin(sel.countries)
    if sel.attacks:
        mask &= df["attacktype1_txt"].isin(sel.attacks)
    if sel.targets:
        mask &= df["targtype1_txt"].isin(sel.targets)
    if sel.groups:
        mask &= df["gname"].isin(sel.groups)
    return mask


def filter_df(df: pd.DataFrame, sel: Selection) -> pd.DataFrame:
    """Apply every global filter. Empty tuples mean 'no restriction'."""
    return df[_mask(df, sel)]


def row_positions(df: pd.DataFrame, sel: Selection) -> np.ndarray:
    """Positions of the selected rows; small to cache, and ``df.iloc[pos]`` equals ``filter_df(df, sel)``."""
    return np.flatnonzero(_mask(df, sel).to_numpy())


def is_unknown(s: pd.Series) -> pd.Series:
    """True where a label is missing or literally 'Unknown'."""
    s = s.astype("object")
    return s.isna() | s.astype(str).str.strip().str.lower().eq("unknown")


# --------------------------------------------------------------------------------------
# KPIs
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Kpis:
    incidents: int
    countries: int
    fatalities: int | None      # sum of valid counts; None when no incident reports one
    fatalities_known: int       # incidents with a valid fatality count
    injuries: int | None
    injuries_known: int
    success_eligible: int       # incidents with a known 0/1 success flag
    success_count: int
    coords_known: int
    groups: int = 0             # distinct named perpetrator groups (Unknown excluded)
    suicide: int = 0            # incidents flagged as suicide attacks

    @property
    def casualties(self) -> int | None:
        """Reported casualties: valid fatalities plus valid injuries (each summed over the incidents that report it)."""
        if self.fatalities is None and self.injuries is None:
            return None
        return (self.fatalities or 0) + (self.injuries or 0)

    @property
    def fatalities_cov(self) -> float | None:
        return self.fatalities_known / self.incidents if self.incidents else None

    @property
    def injuries_cov(self) -> float | None:
        return self.injuries_known / self.incidents if self.incidents else None

    @property
    def coords_cov(self) -> float | None:
        return self.coords_known / self.incidents if self.incidents else None

    @property
    def success_pct(self) -> float | None:
        return 100 * self.success_count / self.success_eligible if self.success_eligible else None


def kpis(fdf: pd.DataFrame) -> Kpis:
    k_known = int(fdf["nkill_v"].notna().sum())
    w_known = int(fdf["nwound_v"].notna().sum())
    succ = fdf["success"].where(fdf["success"].isin([0, 1]))
    return Kpis(
        incidents=int(fdf["eventid"].nunique()),
        countries=int(fdf["country_txt"].nunique()),
        fatalities=int(fdf["nkill_v"].sum()) if k_known else None,
        fatalities_known=k_known,
        injuries=int(fdf["nwound_v"].sum()) if w_known else None,
        injuries_known=w_known,
        success_eligible=int(succ.notna().sum()),
        success_count=int((succ == 1).sum()),
        coords_known=int(fdf["has_xy"].sum()),
        groups=int(fdf.loc[fdf["group_named"], "gname"].nunique()),
        suicide=int((fdf["suicide"] == 1).sum()),
    )


# --------------------------------------------------------------------------------------
# Aggregations used by the charts
# --------------------------------------------------------------------------------------
def yearly(fdf: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """One row per year of the selected period."""
    g = fdf.groupby("iyear", observed=True)
    succ = fdf["success"].where(fdf["success"].isin([0, 1]))
    out = pd.DataFrame({
        "incidents": g.size(),
        "fatalities": g["nkill_v"].sum(min_count=1),
        "injuries": g["nwound_v"].sum(min_count=1),
        "countries": g["country_txt"].nunique(),
        "success_pct": succ.groupby(fdf["iyear"]).mean() * 100,
    })
    out = out.reindex(range(int(years[0]), int(years[1]) + 1))
    out["incidents"] = out["incidents"].fillna(0).astype(int)
    out.index.name = "year"
    return out


def entity_table(fdf: pd.DataFrame, col: str, *, drop_unknown: bool = False) -> pd.DataFrame:
    """Incidents and reported casualties per category, largest first."""
    d = fdf[[col, "nkill_v", "nwound_v"]]
    if drop_unknown:
        d = d[~is_unknown(d[col])]
    g = d.groupby(col, observed=True)
    t = pd.DataFrame({
        "incidents": g.size(),
        "fatalities": g["nkill_v"].sum(min_count=1),
        "injuries": g["nwound_v"].sum(min_count=1),
        "fatal_known": g["nkill_v"].count(),
    })
    t = t[t["incidents"] > 0].sort_values("incidents", ascending=False)
    t.index = t.index.astype(str)
    t.index.name = "label"
    t["share"] = 100 * t["incidents"] / max(len(fdf), 1)
    return t


def ranking(fdf: pd.DataFrame, col: str) -> tuple[pd.DataFrame, int]:
    """Entity table for a Top-N chart: Unknown stays in every total but is left out of the ranking.

    Returns the table without Unknown labels and the number of incidents that were left out.
    """
    return entity_table(fdf, col, drop_unknown=True), int(is_unknown(fdf[col]).sum())


def with_other(t: pd.DataFrame, n: int, other_label: str = "Other") -> pd.DataFrame:
    """Keep the top ``n`` rows and fold the rest into one 'Other (k)' row."""
    if len(t) <= n + 1:   # folding a single row into 'Other (1)' would only hide it
        return t
    head, tail = t.iloc[:n], t.iloc[n:]
    other = pd.DataFrame({
        "incidents": [tail["incidents"].sum()],
        "fatalities": [tail["fatalities"].sum(min_count=1)],
        "injuries": [tail["injuries"].sum(min_count=1)],
        "fatal_known": [tail["fatal_known"].sum()],
        "share": [tail["share"].sum()],
    }, index=[f"{other_label} ({len(tail)})"])
    other.index.name = "label"
    return pd.concat([head, other])


def country_table(fdf: pd.DataFrame) -> pd.DataFrame:
    """Per country: incidents and reported casualties (as entity_table) plus the mean position of its incidents.

    The position places a marker for countries too small to have a polygon on the 1:110m map.
    """
    t = entity_table(fdf, "country_txt")
    pos = fdf.loc[fdf["has_xy"]].groupby("country_txt", observed=True)[["latitude", "longitude"]].mean()
    pos.index = pos.index.astype(str)
    return t.join(pos.rename(columns={"latitude": "lat", "longitude": "lon"}))


def attack_target_matrix(fdf: pd.DataFrame, n_targets: int = 8) -> tuple[pd.DataFrame, int]:
    """Attack type x target type counts (Unknown labels excluded) and the number excluded."""
    keep = ~is_unknown(fdf["attacktype1_txt"]) & ~is_unknown(fdf["targtype1_txt"])
    d = fdf.loc[keep, ["attacktype1_txt", "targtype1_txt"]].astype(str)
    excluded = int((~keep).sum())
    if d.empty:
        return pd.DataFrame(), excluded
    top = d["targtype1_txt"].value_counts().head(n_targets).index
    d["tgt"] = np.where(d["targtype1_txt"].isin(top), d["targtype1_txt"], "Other targets")
    m = pd.crosstab(d["attacktype1_txt"], d["tgt"])
    m = m.loc[m.sum(axis=1).sort_values(ascending=False).index]
    cols = [c for c in top if c in m.columns] + (["Other targets"] if "Other targets" in m.columns else [])
    return m[cols], excluded


FATALITY_BUCKETS = [(0, 0, "0"), (1, 1, "1"), (2, 4, "2-4"), (5, 9, "5-9"), (10, 49, "10-49"), (50, np.inf, "50+")]


def fatality_buckets(fdf: pd.DataFrame) -> pd.DataFrame:
    """Distribution of valid fatality counts per incident, with each bucket's share of deaths."""
    k = fdf["nkill_v"].dropna()
    rows = []
    for lo, hi, label in FATALITY_BUCKETS:
        sel = k[(k >= lo) & (k <= hi)]
        rows.append({"bucket": label, "incidents": int(len(sel)), "fatalities": int(sel.sum())})
    t = pd.DataFrame(rows).set_index("bucket")
    n, deaths = t["incidents"].sum(), t["fatalities"].sum()
    t["pct_incidents"] = 100 * t["incidents"] / n if n else np.nan
    t["pct_fatalities"] = 100 * t["fatalities"] / deaths if deaths else np.nan
    return t


def casualties_by_attack(fdf: pd.DataFrame) -> pd.DataFrame:
    t = entity_table(fdf, "attacktype1_txt")
    t = t[t["fatalities"].notna() | t["injuries"].notna()]
    t["total"] = t[["fatalities", "injuries"]].sum(axis=1)
    return t.sort_values("total", ascending=False)


def suicide_compare(fdf: pd.DataFrame) -> pd.DataFrame:
    """Suicide vs non-suicide incidents (valid counts only)."""
    rows = {}
    for flag, name in ((1, "Suicide attacks"), (0, "Other attacks")):
        d = fdf[fdf["suicide"] == flag]
        k, w = d["nkill_v"].dropna(), d["nwound_v"].dropna()
        rows[name] = {
            "incidents": int(len(d)),
            "share": 100 * len(d) / max(len(fdf), 1),
            "fatal_known": int(len(k)), "fatal_mean": k.mean() if len(k) else np.nan,
            "fatal_median": k.median() if len(k) else np.nan,
            "fatal_ge10": 100 * (k >= 10).mean() if len(k) else np.nan,
            "injury_known": int(len(w)), "injury_mean": w.mean() if len(w) else np.nan,
            "injury_median": w.median() if len(w) else np.nan,
        }
    return pd.DataFrame(rows).T


def bucket_label(v: float) -> str | None:
    for lo, hi, label in FATALITY_BUCKETS:
        if lo <= v <= hi:
            return label
    return None


def casualty_bucket_matrix(fdf: pd.DataFrame) -> pd.DataFrame:
    """Incidents with both counts known, banded by fatalities (rows) and injuries (columns)."""
    d = fdf[["nkill_v", "nwound_v"]].dropna()
    labels = [b[2] for b in FATALITY_BUCKETS]
    edges = [b[0] for b in FATALITY_BUCKETS] + [np.inf]
    rows = pd.cut(d["nkill_v"], bins=edges, labels=labels, right=False)
    cols = pd.cut(d["nwound_v"], bins=edges, labels=labels, right=False)
    return pd.crosstab(rows, cols).reindex(index=labels, columns=labels, fill_value=0)


def attack_fatality_summary(fdf: pd.DataFrame, min_n: int = 5) -> pd.DataFrame:
    """Mean and median reported fatalities per attack type (Unknown excluded), as used by Kruskal-Wallis."""
    d = fdf.loc[~is_unknown(fdf["attacktype1_txt"]), ["attacktype1_txt", "nkill_v"]].dropna()
    d["attacktype1_txt"] = d["attacktype1_txt"].astype(str)
    g = d.groupby("attacktype1_txt")["nkill_v"]
    t = pd.DataFrame({"n": g.size(), "mean": g.mean(), "median": g.median()})
    return t[t["n"] >= min_n].sort_values("mean", ascending=False)


def suicide_buckets(fdf: pd.DataFrame) -> pd.DataFrame:
    """Share of incidents per fatality band for suicide vs other attacks (known counts only)."""
    out = {}
    for flag, name in ((1, "Suicide attacks"), (0, "Other attacks")):
        out[name] = fatality_buckets(fdf[fdf["suicide"] == flag])["pct_incidents"]
    return pd.DataFrame(out)


# --------------------------------------------------------------------------------------
# Comparison with an earlier period (the change badges)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Comparison:
    """What a change badge compares: ``current`` against ``previous`` (None when there is nothing earlier)."""
    current: Selection
    previous: Selection | None
    caption: str


def comparison(sel: Selection, data_years: tuple[int, int]) -> Comparison:
    """The selected period against the period of equal length just before it.

    When the data does not reach back that far (the default 2000-2017 selection), the last selected year is
    compared with the year before it, and the caption says so.
    """
    a, b = sel.years
    length = b - a + 1
    if a - length >= data_years[0]:
        prev = (a - length, a - 1)
        return Comparison(sel, sel.with_years(prev), f"vs. {prev[0]}" if length == 1 else f"vs. {prev[0]}-{prev[1]}")
    if a < b:
        return Comparison(sel.with_years((b, b)), sel.with_years((b - 1, b - 1)), f"{b} vs. {b - 1}")
    return Comparison(sel, None, "no earlier year in the data")


def pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return 100 * (current - previous) / previous


# --------------------------------------------------------------------------------------
# Insights: short, data-driven findings about the selection. The overview lists them all; every other
# page shows the relevant one under a panel title. Each finding names its denominator, and a finding
# whose data is too thin for the current selection is simply left out.
# --------------------------------------------------------------------------------------
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December"]
INSIGHT_TOPICS = ["Trend", "Geography", "Method", "Groups", "Human impact", "Data quality"]


def _share(x: float) -> str:
    return f"{x:.0f}%" if x >= 10 else f"{x:.1f}%"


def _top_named(fdf: pd.DataFrame, col: str) -> tuple[str, int, float] | None:
    """(label, incidents, % of all incidents) of the most common label other than Unknown."""
    t, _ = ranking(fdf, col)
    if not len(t):
        return None
    return str(t.index[0]), int(t["incidents"].iloc[0]), float(t["share"].iloc[0])


def insights(fdf: pd.DataFrame, yr: pd.DataFrame, incidents_change: float | None = None, caption: str = "") -> dict[str, dict]:
    """Findings keyed by name, in reading order. Each is a dict with ``topic``, ``icon``, ``value`` and ``text``
    (shown as a pair on the overview), ``line`` (one sentence for a panel subtitle), and ``tone``:
    "bad" (more harm), "good" (less harm) or "neutral"."""
    n = len(fdf)
    out: dict[str, dict] = {}
    if not n:
        return out

    def add(key: str, topic: str, icon: str, value: str, text: str, line: str, tone: str = "bad") -> None:
        out[key] = {"key": key, "topic": topic, "icon": icon, "value": value, "text": text, "line": line, "tone": tone}

    kv = fdf["nkill_v"].dropna()
    deaths = float(kv.sum())

    # ---------------- Trend ----------------
    if incidents_change is not None:
        up = incidents_change >= 0
        add("change", "Trend", "trend_up" if up else "trend_down", f"{incidents_change:+.1f}%",
            f"{'increase' if up else 'decrease'} in incidents, {caption}",
            f"Incidents {'up' if up else 'down'} {abs(incidents_change):.1f}% ({caption})", "bad" if up else "good")
    multi_year = len(yr) > 1 and yr["incidents"].max() > 0
    if multi_year:
        peak, pn = int(yr["incidents"].idxmax()), int(yr["incidents"].max())
        add("peak", "Trend", "calendar", f"Peak: {peak}", f"most incidents in the selection ({pn:,}, {_share(100 * pn / n)})",
            f"Peak year {peak}: {pn:,} incidents ({_share(100 * pn / n)} of the period)", "neutral")
        first_year, first = int(yr.index[0]), int(yr["incidents"].iloc[0])
        if first > 0 and peak != first_year and pn / first >= 1.5:
            add("growth", "Trend", "timeline", f"{pn / first:.1f}×", f"more incidents in {peak} than in {first_year}",
                f"{pn / first:.1f}× more incidents in {peak} than in {first_year}")
        leth = fdf.groupby("iyear")["nkill_v"].agg(["mean", "count"])
        leth = leth[leth["count"] >= 30]["mean"]
        if len(leth) >= 2 and leth.index[0] != leth.index[-1]:
            a, b = float(leth.iloc[0]), float(leth.iloc[-1])
            add("lethality_trend", "Trend", "fatalities", f"{a:.1f} → {b:.1f}",
                f"fatalities per incident, {leth.index[0]} to {leth.index[-1]} (incidents with a known count)",
                f"Fatalities per incident: {a:.1f} in {leth.index[0]}, {b:.1f} in {leth.index[-1]}", "bad" if b > a else "good")
    else:
        m = fdf["imonth"].value_counts()
        if len(m):
            add("peak", "Trend", "calendar", f"Peak: {MONTHS[int(m.idxmax()) - 1]}", f"busiest month of the year ({int(m.max()):,} incidents)",
                f"Busiest month: {MONTHS[int(m.idxmax()) - 1]} ({int(m.max()):,} incidents)", "neutral")
    months = fdf["imonth"].value_counts()
    if multi_year and len(months) == 12:
        top_m = int(months.idxmax())
        add("month", "Trend", "calendar", MONTHS[top_m - 1], f"is the busiest calendar month ({_share(100 * months.max() / n)} of incidents)",
            f"{MONTHS[top_m - 1]} is the busiest month ({_share(100 * months.max() / n)}); {MONTHS[int(months.idxmin()) - 1]} the quietest",
            "neutral")

    # ---------------- Geography ----------------
    regions = entity_table(fdf, "region_txt")
    if len(regions) > 1:
        top = regions.head(2)
        add("regions", "Geography", "regions", _share(top["share"].sum()), f"of incidents in {top.index[0]} and {top.index[1]}",
            f"{top.index[0]} and {top.index[1]}: {_share(top['share'].sum())} of incidents")
    countries = entity_table(fdf, "country_txt")
    if len(countries) > 1:
        c, r = countries.index[0], countries.iloc[0]
        fat = f", {_share(100 * r['fatalities'] / deaths)} of reported fatalities" if deaths and pd.notna(r["fatalities"]) else ""
        add("top_country", "Geography", "flag", _share(r["share"]), f"of incidents in {c}{fat}", f"{c}: {_share(r['share'])} of incidents{fat}")
    if len(countries) >= 12:
        s10 = float(countries["share"].head(10).sum())
        add("top10", "Geography", "travel_explore", _share(s10), f"of incidents in the 10 most affected of {len(countries)} countries",
            f"The 10 most affected countries hold {_share(s10)} of incidents")
    eligible = countries[countries["fatal_known"] >= 50]
    if len(eligible) >= 3:
        leth = (eligible["fatalities"] / eligible["fatal_known"]).sort_values(ascending=False)
        c = leth.index[0]
        add("deadliest_country", "Geography", "fatalities", f"{leth.iloc[0]:.1f}",
            f"fatalities per incident in {c}, the highest of countries with 50+ known counts",
            f"Deadliest per incident: {c} ({leth.iloc[0]:.1f} fatalities per incident)")
    cities, _ = city_table(fdf, 12)
    if len(cities) >= 3:
        c0, n0 = cities.index[0], int(cities["incidents"].iloc[0])
        k, total = 0, 0
        for v in cities["incidents"].iloc[1:]:
            if total + v > n0:
                break
            total += int(v)
            k += 1
        tail = f", more than the next {k} cities combined" if k >= 2 else ", the most of any city"
        add("top_city", "Geography", "city", f"{n0:,}", f"incidents in {c0}{tail}", f"{c0}: {n0:,} incidents{tail}", "neutral")

    # ---------------- Method ----------------
    top_attack = _top_named(fdf, "attacktype1_txt")
    if top_attack:
        add("top_attack", "Method", "attack", _share(top_attack[2]), f"of incidents are {top_attack[0].lower()}",
            f"{top_attack[0]} is the main method ({_share(top_attack[2])} of incidents)", "neutral")
    means = attack_fatality_summary(fdf, min_n=30)
    if len(means) >= 2:
        a, mean = str(means.index[0]), float(means["mean"].iloc[0])
        overall = float(kv.mean()) if len(kv) else 0.0
        times = f", {mean / overall:.1f}× the average" if overall > 0 else ""
        add("lethal_attack", "Method", "fatalities", f"{mean:.1f}", f"fatalities per {a.lower()} incident{times}",
            f"Deadliest method: {a} ({mean:.1f} fatalities per incident{times})")
    top_weapon = _top_named(fdf, "weaptype1_txt")
    if top_weapon:
        add("top_weapon", "Method", "bomb", _share(top_weapon[2]), f"of incidents use {top_weapon[0].split(' (')[0].lower()}",
            f"{top_weapon[0].split(' (')[0]} are used in {_share(top_weapon[2])} of incidents", "neutral")
    top_target = _top_named(fdf, "targtype1_txt")
    if top_target:
        add("top_target", "Method", "target", _share(top_target[2]), f"of incidents target {top_target[0].lower()}",
            f"Most frequent target: {top_target[0]} ({_share(top_target[2])})", "neutral")
    matrix, _ = attack_target_matrix(fdf, n_targets=8)
    if matrix.size and matrix.to_numpy().max() > 0:
        i, j = np.unravel_index(int(np.argmax(matrix.to_numpy())), matrix.shape)
        v = int(matrix.iat[i, j])
        add("top_pair", "Method", "crosshair", f"{v:,}", f"{matrix.index[i].lower()} attacks on {matrix.columns[j].lower()}, the most common pairing",
            f"Most common pairing: {matrix.index[i]} on {matrix.columns[j]} ({v:,})", "neutral")

    # ---------------- Groups ----------------
    named = fdf.loc[fdf["group_named"], "gname"].astype(str)
    unattributed = 100 * (1 - len(named) / n)
    add("unattributed", "Groups", "unknown", _share(unattributed), "of incidents have no attributed group",
        f"{_share(unattributed)} of incidents have no attributed group", "neutral")
    if len(named):
        counts = named.value_counts()
        k = min(5, len(counts))
        add("top_groups", "Groups", "groups", f"{k} group{'s' if k > 1 else ''}",
            f"account for {_share(100 * counts.head(k).sum() / len(named))} of incidents with a named group",
            f"The top {k} groups: {_share(100 * counts.head(k).sum() / len(named))} of attributed incidents", "neutral")
        add("top_group", "Groups", "groups", f"{int(counts.iloc[0]):,}", f"incidents by {counts.index[0]}, the most active group",
            f"Most active: {counts.index[0]} ({int(counts.iloc[0]):,} incidents)", "neutral")
        g = fdf[fdf["group_named"]].assign(gname=lambda d: d["gname"].astype(str)).groupby("gname")["nkill_v"].sum(min_count=1).dropna()
        if len(g) and g.max() > 0:
            add("deadliest_group", "Groups", "fatalities", f"{int(g.max()):,}", f"reported fatalities attributed to {g.idxmax()}",
                f"Deadliest group: {g.idxmax()} ({int(g.max()):,} reported fatalities)")
        cl = fdf.loc[fdf["group_named"], "claimed"]
        cl = cl[cl.isin([0, 1])]
        if len(cl) >= 30:
            add("claimed", "Groups", "claim", _share(100 * cl.mean()), "of attributed incidents were claimed by the group",
                f"Responsibility claimed in {_share(100 * cl.mean())} of attributed incidents", "neutral")

    # ---------------- Human impact ----------------
    if len(kv) and deaths > 0:
        big = kv[kv >= 10]
        if len(big):
            add("heavy_tail", "Human impact", "warning", _share(100 * big.sum() / deaths),
                f"of reported fatalities come from the {_share(100 * len(big) / len(kv))} of incidents with 10 or more",
                f"{_share(100 * len(big) / len(kv))} of incidents cause {_share(100 * big.sum() / deaths)} of fatalities (10+ each)")
        zero = 100 * float((kv == 0).mean())
        add("no_deaths", "Human impact", "casualties", _share(zero), "of incidents with a known count caused no fatality",
            f"{_share(zero)} of incidents with a known count caused no fatality", "neutral")
        sui = fdf["suicide"] == 1
        if 0 < sui.sum() < n:
            s_share = 100 * float(sui.mean())
            s_deaths = 100 * float(fdf.loc[sui, "nkill_v"].sum()) / deaths
            add("suicide", "Human impact", "fatalities", _share(s_deaths), f"of fatalities come from suicide attacks ({_share(s_share)} of incidents)",
                f"Suicide attacks: {_share(s_share)} of incidents, {_share(s_deaths)} of fatalities")
    succ = fdf["success"][fdf["success"].isin([0, 1])]
    if len(succ):
        add("success", "Human impact", "verified", _share(100 * succ.mean()), "of incidents succeeded (GTD tactical success)",
            f"{_share(100 * succ.mean())} of incidents succeeded (tactical success flag)")

    # ---------------- Data quality ----------------
    w_missing = 100 * float(fdf["nwound_v"].isna().mean())
    k_missing = 100 * float(fdf["nkill_v"].isna().mean())
    worst, label = (w_missing, "injury") if w_missing >= k_missing else (k_missing, "fatality")
    add("coverage", "Data quality", "data", _share(worst), f"of incidents have no valid {label} count; totals are lower bounds",
        f"No valid {label} count for {_share(worst)} of incidents: totals are lower bounds", "neutral")
    return out


def overview_insights(fdf: pd.DataFrame, yr: pd.DataFrame, incidents_change: float | None, caption: str) -> list[dict]:
    """The four headline findings of the mockup's Key Insights card (trend, concentration, groups, peak)."""
    found = insights(fdf, yr, incidents_change, caption)
    return [found[k] for k in ("change", "regions", "top_groups", "peak") if k in found]


# --------------------------------------------------------------------------------------
# Page aggregates
# --------------------------------------------------------------------------------------
def attack_mix(fdf: pd.DataFrame, n: int = 5) -> list[tuple[str, int, float]]:
    """The n most common named attack types plus 'Other' (the rest, Unknown included): (label, incidents, %)."""
    total = len(fdf)
    if not total:
        return []
    named, _ = ranking(fdf, "attacktype1_txt")
    rows = [(str(lab), int(c), 100 * c / total) for lab, c in named["incidents"].head(n).items()]
    rest = total - sum(r[1] for r in rows)
    if rest:
        rows.append(("Other", rest, 100 * rest / total))
    return rows


def _year_index(years: tuple[int, int]) -> pd.Index:
    return pd.Index(range(int(years[0]), int(years[1]) + 1), name="year")


def groups_by_year(fdf: pd.DataFrame, years: tuple[int, int], n: int = 5) -> pd.DataFrame:
    """Incidents per year for the n largest named groups in the selection (columns ordered by size)."""
    named = fdf.loc[fdf["group_named"], ["iyear", "gname"]].astype({"gname": str})
    top = named["gname"].value_counts().head(n).index
    t = pd.crosstab(named["iyear"], named["gname"]).reindex(columns=top)
    return t.reindex(_year_index(years), fill_value=0)


def attribution_by_year(fdf: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    """Share of incidents with a named group, and share of those whose responsibility was claimed (known flags only)."""
    named = fdf[fdf["group_named"]]
    claimed = named["claimed"].where(named["claimed"].isin([0, 1]))
    out = pd.DataFrame({"attributed_pct": 100 * fdf.groupby("iyear")["group_named"].mean(),
                        "claimed_pct": 100 * claimed.groupby(named["iyear"]).mean()})
    return out.reindex(_year_index(years))


def group_summary(fdf: pd.DataFrame, n: int = 8) -> pd.DataFrame:
    """The n largest named groups: incidents, reported fatalities, fatalities per incident with a count, years, main country."""
    d = fdf[fdf["group_named"]]
    if d.empty:
        return pd.DataFrame(columns=["incidents", "fatalities", "lethality", "first", "last", "country"])
    d = d.assign(gname=d["gname"].astype(str), country_txt=d["country_txt"].astype(str))
    g = d.groupby("gname")
    t = pd.DataFrame({"incidents": g.size(), "fatalities": g["nkill_v"].sum(min_count=1), "lethality": g["nkill_v"].mean(),
                      "first": g["iyear"].min(), "last": g["iyear"].max(),
                      "country": g["country_txt"].agg(lambda s: s.value_counts().index[0])})
    return t.sort_values("incidents", ascending=False).head(n)


def month_table(fdf: pd.DataFrame) -> pd.DataFrame:
    m = fdf["imonth"].value_counts().reindex(range(1, 13), fill_value=0)
    return pd.DataFrame({"month": [x[:3] for x in MONTHS], "incidents": m.to_numpy(),
                         "share": 100 * m.to_numpy() / max(len(fdf), 1)})


def attack_mix_by_year(fdf: pd.DataFrame, years: tuple[int, int], n: int = 5) -> pd.DataFrame:
    """Share (%) of each year's incidents by attack type: the n largest named types, then Other (Unknown included)."""
    top = [lab for lab, _, _ in attack_mix(fdf, n) if lab != "Other"]
    names = fdf["attacktype1_txt"].astype(str)
    lab = names.where(names.isin(top), "Other")
    t = pd.crosstab(fdf["iyear"], lab, normalize="index") * 100
    cols = top + (["Other"] if "Other" in t.columns else [])
    return t.reindex(columns=cols).reindex(_year_index(years))


def rates_by_year(fdf: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    succ = fdf["success"].where(fdf["success"].isin([0, 1]))
    out = pd.DataFrame({"success_pct": 100 * succ.groupby(fdf["iyear"]).mean(),
                        "suicide_pct": 100 * (fdf["suicide"] == 1).groupby(fdf["iyear"]).mean()})
    return out.reindex(_year_index(years))


def city_table(fdf: pd.DataFrame, n: int = 10) -> tuple[pd.DataFrame, int]:
    """Top named cities ("City, Country") and the number of incidents whose city is unknown."""
    known = ~is_unknown(fdf["city"])
    d = fdf.loc[known, ["city", "country_txt", "nkill_v"]].astype({"city": str, "country_txt": str})
    g = d.groupby(["city", "country_txt"])
    t = pd.DataFrame({"incidents": g.size(), "fatalities": g["nkill_v"].sum(min_count=1)})
    t = t.sort_values("incidents", ascending=False).head(n)
    t.index = [f"{c}, {k}" for c, k in t.index]
    return t, int((~known).sum())


RECORD_SORTS = {"Deadliest first": ("nkill_v", False), "Most recent first": ("eventid", False), "Oldest first": ("eventid", True)}


def records(fdf: pd.DataFrame, query: str = "", sort: str = "Deadliest first") -> pd.DataFrame:
    """Incident rows for the explorer, optionally narrowed by a case-insensitive text search."""
    d = fdf
    q = query.strip().lower()
    if q:
        hit = np.zeros(len(d), dtype=bool)
        for col in ("city", "country_txt", "gname", "provstate", "target1", "attacktype1_txt"):
            hit |= d[col].astype(str).str.lower().str.contains(q, regex=False, na=False).to_numpy()
        if q.isdigit():
            hit |= (d["eventid"].astype(str) == q).to_numpy()
        d = d[hit]
    col, asc = RECORD_SORTS.get(sort, RECORD_SORTS["Deadliest first"])
    d = d.sort_values([col, "eventid"], ascending=[asc, False], na_position="last")
    day = d["iday"].astype("Int64").astype(str).str.zfill(2).replace("<NA>", "--")
    city = d["city"].astype(str).where(~is_unknown(d["city"]), "Unknown city")
    return pd.DataFrame({
        "eventid": d["eventid"].to_numpy(),
        "date": (d["iyear"].astype(str) + "-" + d["imonth"].astype(str).str.zfill(2) + "-" + day).to_numpy(),
        "place": (city + ", " + d["country_txt"].astype(str)).to_numpy(),
        "attack": d["attacktype1_txt"].astype(str).to_numpy(), "target": d["targtype1_txt"].astype(str).to_numpy(),
        "group": d["gname"].astype(str).to_numpy(), "killed": d["nkill_v"].to_numpy(), "injured": d["nwound_v"].to_numpy(),
    })


def coverage_rows(fdf: pd.DataFrame) -> list[tuple[str, float, str]]:
    """Share of incidents in view that carry each piece of information."""
    if not len(fdf):
        return []
    rows = [("Fatality count", fdf["nkill_v"].notna().mean(), "valid nkill (present, >= 0, whole number)"),
            ("Injury count", fdf["nwound_v"].notna().mean(), "valid nwound"),
            ("Coordinates", fdf["has_xy"].mean(), "latitude and longitude present and in range"),
            ("Exact day", fdf["iday"].notna().mean(), "iday recorded (0 placeholders were cleaned to missing)"),
            ("Named city", (~is_unknown(fdf["city"])).mean(), "city other than Unknown"),
            ("Named group", fdf["group_named"].mean(), "perpetrator group other than Unknown"),
            ("Known weapon type", (~is_unknown(fdf["weaptype1_txt"])).mean(), "weapon type other than Unknown"),
            ("Claim flag", fdf["claimed"].isin([0, 1]).mean(), "claimed is 0 or 1 (-9 was cleaned to missing)"),
            ("Property damage flag", fdf["property"].isin([0, 1]).mean(), "property is 0 or 1 (-9 was cleaned to missing)")]
    return [(label, float(frac), tip) for label, frac, tip in rows]


def missing_by_year(fdf: pd.DataFrame, years: tuple[int, int]) -> pd.DataFrame:
    g = fdf.groupby("iyear")
    return pd.DataFrame({"fatalities": 100 * g["nkill_v"].apply(lambda s: s.isna().mean()),
                         "injuries": 100 * g["nwound_v"].apply(lambda s: s.isna().mean())}).reindex(_year_index(years))


def reconciliation(fdf: pd.DataFrame) -> list[dict]:
    """The selection's totals under the three counting rules used across the project's deliverables.

    Dashboard: valid counts only (fractional counts are invalid). Notebook: raw sums. Power BI: nwound stored as
    a whole-number column, which truncates 8.5 to 8. All three are computed here from the data.
    """
    def total(s: pd.Series) -> int | None:
        v = s.sum(min_count=1)
        return None if pd.isna(v) else int(v)

    k = kpis(fdf)
    raw_k, raw_w, pbi_w = total(fdf["nkill"]), total(fdf["nwound"]), total(np.floor(fdf["nwound"]))
    both = lambda a, b: None if a is None and b is None else (a or 0) + (b or 0)
    rows = [("Incidents", k.incidents, len(fdf), len(fdf)), ("Fatalities", k.fatalities, raw_k, raw_k),
            ("Injuries", k.injuries, raw_w, pbi_w), ("Casualties", k.casualties, both(raw_k, raw_w), both(raw_k, pbi_w))]
    return [{"measure": m, "dashboard": d, "notebook": nb, "power_bi": pbi} for m, d, nb, pbi in rows]


# --------------------------------------------------------------------------------------
# Statistical analysis (the four primary tests of the notebook, section 9)
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class TestResult:
    key: str
    name: str
    question: str
    effect_name: str
    effect_lo: float
    effect_hi: float
    n: int | None = None
    statistic: float | None = None
    stat_name: str = ""
    p_raw: float | None = None
    p_holm: float | None = None
    effect: float | None = None
    detail: dict = field(default_factory=dict)
    note: str = ""          # why a test could not be run, or a diagnostic remark

    @property
    def ok(self) -> bool:
        return self.effect is not None and self.p_raw is not None


MIN_N = 30


def holm_adjust(p: list[float | None]) -> list[float | None]:
    idx = [i for i, v in enumerate(p) if v is not None and np.isfinite(v)]
    order = sorted(idx, key=lambda i: p[i])
    m, running, adj = len(order), 0.0, {}
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return [adj.get(i) for i in range(len(p))]


def _spearman(fdf: pd.DataFrame) -> TestResult:
    base = dict(key="spearman", name="Spearman correlation", effect_name="rho", effect_lo=-1, effect_hi=1,
                question="Do incidents with more reported fatalities also report more injuries?")
    pair = fdf[["nkill_v", "nwound_v"]].dropna()
    if len(pair) < MIN_N or pair["nkill_v"].nunique() < 2 or pair["nwound_v"].nunique() < 2:
        return TestResult(**base, n=len(pair), note="Not enough incidents with both counts known.")
    r = stats.spearmanr(pair["nkill_v"], pair["nwound_v"])
    return TestResult(**base, n=len(pair), statistic=float(r.statistic), stat_name="rho", p_raw=float(r.pvalue),
                      effect=float(r.statistic), detail={"excluded": int(len(fdf) - len(pair))})


def _chi2(fdf: pd.DataFrame) -> TestResult:
    base = dict(key="chi2", name="Chi-square test of independence", effect_name="Cramer's V (bias-corrected)",
                effect_lo=0, effect_hi=1, question="Is the attack type linked to the type of target?")
    keep = ~is_unknown(fdf["attacktype1_txt"]) & ~is_unknown(fdf["targtype1_txt"])
    d = fdf.loc[keep, ["attacktype1_txt", "targtype1_txt"]].astype(str)
    ct = pd.crosstab(d["attacktype1_txt"], d["targtype1_txt"])
    ct = ct.loc[ct.sum(axis=1) > 0, ct.sum(axis=0) > 0]
    n = int(ct.values.sum())
    if ct.shape[0] < 2 or ct.shape[1] < 2 or n < MIN_N:
        return TestResult(**base, n=n, note="Needs at least two attack types and two target types.")
    chi2, p, dof, expected = stats.chi2_contingency(ct.values, correction=False)
    r, c = ct.shape
    phi2 = chi2 / n
    phi2c = max(0.0, phi2 - (c - 1) * (r - 1) / (n - 1))
    rc, cc = r - (r - 1) ** 2 / (n - 1), c - (c - 1) ** 2 / (n - 1)
    v_corr = float(np.sqrt(phi2c / min(cc - 1, rc - 1))) if min(cc, rc) > 1 else 0.0
    sparse = float((expected < 5).mean())
    ratio = pd.DataFrame(ct.values / expected, index=ct.index, columns=ct.columns).stack()
    obs = ct.stack()
    pairs = pd.DataFrame({"ratio": ratio, "observed": obs})
    pairs = pairs[pairs["observed"] >= 200].sort_values("ratio", ascending=False).head(4)
    top_pairs = [(a, t, float(row.ratio), int(row.observed)) for (a, t), row in pairs.iterrows()]
    return TestResult(**base, n=n, statistic=float(chi2), stat_name=f"chi2 (df={dof})", p_raw=float(p), effect=v_corr,
                      detail={"v_plain": float(np.sqrt(phi2 / min(r - 1, c - 1))), "dof": int(dof), "shape": (r, c),
                              "sparse_share": sparse, "excluded": int((~keep).sum()), "top_pairs": top_pairs},
                      note="Asymptotic p-value; many sparse cells" if sparse > 0.2 or expected.min() < 1 else "")


def _mannwhitney(fdf: pd.DataFrame) -> TestResult:
    base = dict(key="mwu", name="Mann-Whitney U test", effect_name="rank-biserial r", effect_lo=-1, effect_hi=1,
                question="Do suicide attacks differ from other attacks in reported fatalities?")
    d = fdf[["suicide", "nkill_v"]].dropna()
    a, b = d.loc[d["suicide"] == 1, "nkill_v"], d.loc[d["suicide"] == 0, "nkill_v"]
    if len(a) < 5 or len(b) < 5:
        return TestResult(**base, n=len(d), note="Needs at least 5 suicide and 5 other incidents with a known count.")
    u = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
    rb = 2 * float(u.statistic) / (len(a) * len(b)) - 1
    return TestResult(**base, n=len(d), statistic=float(u.statistic), stat_name="U", p_raw=float(u.pvalue), effect=rb,
                      detail={"n_a": len(a), "n_b": len(b), "median_a": float(a.median()), "median_b": float(b.median()),
                              "mean_a": float(a.mean()), "mean_b": float(b.mean()), "prob_superiority": (rb + 1) / 2})


def _kruskal(fdf: pd.DataFrame) -> TestResult:
    base = dict(key="kw", name="Kruskal-Wallis test", effect_name="rank eta-squared (H)", effect_lo=0, effect_hi=1,
                question="Do reported fatalities differ across attack types?")
    d = fdf.loc[~is_unknown(fdf["attacktype1_txt"]), ["attacktype1_txt", "nkill_v"]].dropna()
    d["attacktype1_txt"] = d["attacktype1_txt"].astype(str)
    counts = d["attacktype1_txt"].value_counts()
    d = d[d["attacktype1_txt"].isin(counts[counts >= 5].index)]
    groups = {k: g["nkill_v"].to_numpy() for k, g in d.groupby("attacktype1_txt")}
    if len(groups) < 2 or len(d) < MIN_N:
        return TestResult(**base, n=len(d), note="Needs at least two attack types with 5 or more known counts.")
    h = stats.kruskal(*groups.values())
    k, n = len(groups), len(d)
    eta = max(0.0, (float(h.statistic) - k + 1) / (n - k))
    med = {g: float(np.median(v)) for g, v in groups.items()}
    mean = {g: float(np.mean(v)) for g, v in groups.items()}
    return TestResult(**base, n=n, statistic=float(h.statistic), stat_name=f"H (df={k - 1})", p_raw=float(h.pvalue), effect=eta,
                      detail={"groups": k, "top_mean": max(mean, key=mean.get), "top_mean_value": max(mean.values()),
                              "top_median": max(med, key=med.get), "top_median_value": max(med.values())})


def run_stats(fdf: pd.DataFrame) -> list[TestResult]:
    """Run the four primary tests on the current selection and Holm-adjust their p-values."""
    results = [_spearman(fdf), _chi2(fdf), _mannwhitney(fdf), _kruskal(fdf)]
    adj = holm_adjust([r.p_raw for r in results])
    return [TestResult(**{**r.__dict__, "p_holm": a}) for r, a in zip(results, adj, strict=True)]

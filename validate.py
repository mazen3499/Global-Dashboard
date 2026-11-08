"""Independent validation of the dashboard's data layer and app.

Run:  python validate.py          (exit code 0 = every check passed)

The checks recompute every figure with plain pandas straight from the CSV and compare it with what
core.py (and therefore the dashboard) produces. Notebook reference values below are only used here,
as expected results; the app itself never hard-codes a statistic.
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
import pandas as pd
from scipy import stats

import core

warnings.filterwarnings("ignore")
RESULTS: list[tuple[bool, str]] = []


def check(ok: bool, name: str, detail: str = "") -> bool:
    RESULTS.append((bool(ok), name))
    print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    return bool(ok)


def close(a, b, tol=1e-3) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


# --------------------------------------------------------------------------------------
print("== 1. Data integrity ==")
raw = core.read_raw()
print(f"Data source: {core.data_path().relative_to(core.APP_DIR) if core.data_path().is_relative_to(core.APP_DIR) else core.data_path()}")
df = core.load_data()
check(raw.shape == (111_855, 54), "CSV has 111,855 rows and 54 columns", str(raw.shape))
check(list(raw.columns[:30]) == core.BASE_COLUMNS, "first 30 CSV columns are the 30 analysis columns of the notebook")
check(df.shape[0] == len(raw), "loader keeps every row")
check((int(df.iyear.min()), int(df.iyear.max())) == (2000, 2017) and df.iyear.nunique() == 18, "period is 2000-2017 (18 years)")
check(df.eventid.is_unique and df.eventid.nunique() == len(df), "eventid is unique")
check(not (df.claimed == -9).any() and not (df.property == -9).any(), "no -9 sentinel codes left in claimed / property")
check(not (df.iday == 0).any(), "no iday = 0 placeholders left")
for code, label in [("country", "country_txt"), ("region", "region_txt"), ("attacktype1", "attacktype1_txt"),
                    ("targtype1", "targtype1_txt"), ("weaptype1", "weaptype1_txt")]:
    one_to_one = df.groupby(code)[label].nunique().max() == 1 and df.groupby(label, observed=True)[code].nunique().max() == 1
    check(one_to_one, f"{code} code and {label} map one-to-one")
check(df.latitude.dropna().between(-90, 90).all() and df.longitude.dropna().between(-180, 180).all(), "coordinates are within valid ranges")
check(int(df.has_xy.sum()) == int(df.latitude.notna().sum()) == int(df.longitude.notna().sum()), "has_xy matches rows with coordinates", f"{int(df.has_xy.sum()):,} with coordinates")
frac_w = df[(df.nwound.notna()) & (df.nwound_v.isna())]
check(len(frac_w) == 2 and set(frac_w.nwound) == {8.5}, "exactly 2 fractional nwound values (8.5) are treated as invalid", f"event ids {list(frac_w.eventid)}")
check((df.nkill_v.dropna() >= 0).all() and (df.nwound_v.dropna() >= 0).all() and (df.nkill_v.dropna() % 1 == 0).all(), "valid counts are whole numbers >= 0")
check(df.nkill_v.isna().sum() == raw.nkill.isna().sum() and df.nwound_v.isna().sum() == raw.nwound.isna().sum() + 2, "missing counts stay missing (never replaced with zero)")
# the notebook's engineered columns follow the same rule
complete = (df.nkill_v.notna() & df.nwound_v.notna()).astype(int)
check((raw.casualty_data_complete == complete).all(), "engineered casualty_data_complete equals the rule used here")
tot = df.nkill_v + df.nwound_v
check(np.allclose(raw.total_casualties.fillna(-1), tot.fillna(-1)), "engineered total_casualties equals nkill + nwound where both are valid")
check(((raw.nkill_missing == 1) == df.nkill_v.isna()).all() and ((raw.nwound_missing == 1) == df.nwound_v.isna()).all(), "engineered *_missing flags equal the rule used here")

# --------------------------------------------------------------------------------------
print("\n== 2. KPIs against independent pandas ==")
SELECTIONS = {
    "all data": core.Selection(years=(2000, 2017)),
    "2014-2017": core.Selection(years=(2014, 2017)),
    "single year 2005": core.Selection(years=(2005, 2005)),
    "Iraq": core.Selection(years=(2000, 2017), countries=("Iraq",)),
    "South Asia + Southeast Asia": core.Selection(years=(2000, 2017), regions=("South Asia", "Southeast Asia")),
    "Bombing/Explosion on Police": core.Selection(years=(2008, 2016), attacks=("Bombing/Explosion",), targets=("Police",)),
    "Sub-Saharan Africa 2010-2017": core.Selection(years=(2010, 2017), regions=("Sub-Saharan Africa",)),
}


def independent_mask(sel: core.Selection) -> pd.Series:
    m = (raw.iyear >= sel.years[0]) & (raw.iyear <= sel.years[1])
    if sel.regions: m &= raw.region_txt.isin(sel.regions)
    if sel.countries: m &= raw.country_txt.isin(sel.countries)
    if sel.attacks: m &= raw.attacktype1_txt.isin(sel.attacks)
    if sel.targets: m &= raw.targtype1_txt.isin(sel.targets)
    return m


def valid(s: pd.Series) -> pd.Series:
    return s[s.notna() & (s >= 0) & (s % 1 == 0)]


for name, sel in SELECTIONS.items():
    f = core.filter_df(df, sel)
    k = core.kpis(f)
    r = raw[independent_mask(sel)]
    kv, wv = valid(r.nkill), valid(r.nwound)
    ok = (k.incidents == r.eventid.nunique() == len(f) and k.countries == r.country_txt.nunique()
          and k.fatalities == int(kv.sum()) and k.injuries == int(wv.sum())
          and k.fatalities_known == len(kv) and k.injuries_known == len(wv)
          and k.success_count == int((r.success == 1).sum()) and k.success_eligible == int(r.success.isin([0, 1]).sum())
          and k.coords_known == int(r.latitude.notna().sum()))
    check(ok, f"KPIs: {name}", f"{k.incidents:,} incidents, {k.fatalities:,} fatalities, {k.injuries:,} injuries, {k.countries} countries")

# --------------------------------------------------------------------------------------
print("\n== 3. Chart data adds up to the filtered data ==")
for name, sel in SELECTIONS.items():
    f = core.filter_df(df, sel)
    k = core.kpis(f)
    yr = core.yearly(f, sel.years)
    parts = []
    parts.append(int(yr.incidents.sum()) == k.incidents)
    parts.append(int(yr.fatalities.sum()) == k.fatalities and int(yr.injuries.sum()) == k.injuries)
    parts.append(list(yr.index) == list(range(sel.years[0], sel.years[1] + 1)))
    for col in ("attacktype1_txt", "targtype1_txt", "weaptype1_txt", "country_txt", "region_txt"):
        t = core.entity_table(f, col)
        parts.append(int(t.incidents.sum()) == k.incidents)
        parts.append(int(core.with_other(t, 5).incidents.sum()) == k.incidents)
        parts.append(int(t.fatalities.sum()) == k.fatalities)
    parts.append(int(core.country_table(f).incidents.sum()) == k.incidents)
    b = core.fatality_buckets(f)
    parts.append(int(b.incidents.sum()) == k.fatalities_known and int(b.fatalities.sum()) == k.fatalities)
    m, excluded = core.attack_target_matrix(f, n_targets=8)
    parts.append(int(m.values.sum()) + excluded == k.incidents)
    ca = core.casualties_by_attack(f)
    parts.append(int(ca.fatalities.sum()) == k.fatalities and int(ca.injuries.sum()) == k.injuries)
    sc = core.suicide_compare(f)
    parts.append(int(sc.incidents.sum()) == k.incidents)
    check(all(parts), f"chart totals: {name}", f"{sum(parts)}/{len(parts)} sub-checks")

# --------------------------------------------------------------------------------------
print("\n== 4. Filters, missing data and empty selections ==")
empty = core.filter_df(df, core.Selection(years=(2000, 2000), regions=("Australasia & Oceania",), attacks=("Hijacking",), targets=("Telecommunication",)))
ke = core.kpis(empty)
check(len(empty) == 0 and ke.incidents == 0 and ke.fatalities is None and ke.success_pct is None, "empty selection gives zero incidents and no invented totals")
check(len(core.overview_insights(empty, core.yearly(empty, (2000, 2000)), None, "")) == 0, "empty selection yields no insights and no error")
unk = df[df.nkill.isna()]
ku = core.kpis(unk)
check(ku.fatalities is None and ku.fatalities_known == 0 and ku.incidents == len(unk), "all-unknown fatalities are reported as unknown (None), not zero", f"{len(unk):,} incidents without a count")
inc = core.filter_df(df, core.Selection(years=(2000, 2017), countries=("Iraq",)))
check(set(inc.country_txt.astype(str)) == {"Iraq"}, "country filter returns only that country")
ys = core.filter_df(df, core.Selection(years=(2003, 2005)))
check(int(ys.iyear.min()) == 2003 and int(ys.iyear.max()) == 2005, "year range is inclusive on both ends")
check(len(core.filter_df(df, core.Selection(years=(2000, 2017)))) == len(df), "default selection keeps all rows")

# --------------------------------------------------------------------------------------
print("\n== 5. Statistical tests against the notebook ==")
NOTEBOOK = {"spearman": dict(n=103_582, rho=0.3582), "chi2": dict(n=102_212, chi2=26_938.163, v=0.1940, vc=0.1935),
            "mwu": dict(n=107_688, u=537_640_934.5, rb=0.6639), "kw": dict(n=103_553, h=9_185.645, eta=0.0886)}
res = {r.key: r for r in core.run_stats(df)}
# (a) the notebook ran Spearman on raw nkill/nwound; reproduce that exactly
pair = df[["nkill", "nwound"]].dropna()
rho_raw = stats.spearmanr(pair.nkill, pair.nwound).statistic
check(len(pair) == NOTEBOOK["spearman"]["n"] and close(rho_raw, NOTEBOOK["spearman"]["rho"], 5e-5), "Spearman on raw columns reproduces the notebook", f"n={len(pair):,} rho={rho_raw:.4f}")
# (b) the dashboard applies the validity rule: 2 fewer pairs, identical to 3 decimals
s = res["spearman"]
check(s.n == NOTEBOOK["spearman"]["n"] - 2 and close(s.effect, NOTEBOOK["spearman"]["rho"], 2e-4), "Spearman in the dashboard (valid counts only) differs only by the 2 fractional records", f"n={s.n:,} rho={s.effect:.4f}")
c = res["chi2"]
check(c.n == NOTEBOOK["chi2"]["n"] and close(c.statistic, NOTEBOOK["chi2"]["chi2"], 5e-3) and close(c.detail["v_plain"], NOTEBOOK["chi2"]["v"], 5e-4) and close(c.effect, NOTEBOOK["chi2"]["vc"], 5e-4),
      "Chi-square, Cramer's V and bias-corrected V match the notebook", f"chi2={c.statistic:,.3f} V={c.detail['v_plain']:.4f} Vc={c.effect:.4f}")
m = res["mwu"]
check(m.n == NOTEBOOK["mwu"]["n"] and close(m.statistic, NOTEBOOK["mwu"]["u"], 1.0) and close(m.effect, NOTEBOOK["mwu"]["rb"], 5e-5), "Mann-Whitney U and rank-biserial match the notebook", f"U={m.statistic:,.1f} r={m.effect:.4f}")
kw = res["kw"]
check(kw.n == NOTEBOOK["kw"]["n"] and close(kw.statistic, NOTEBOOK["kw"]["h"], 5e-3) and close(kw.effect, NOTEBOOK["kw"]["eta"], 5e-5), "Kruskal-Wallis H and eta-squared match the notebook", f"H={kw.statistic:,.3f} eta2={kw.effect:.4f}")
check(all(r.p_holm is not None and r.p_holm < 0.05 for r in res.values()), "all four tests remain significant after Holm adjustment (as in the notebook)")
p_in = [0.01, 0.04, 0.03, 0.005]
check(np.allclose(core.holm_adjust(p_in), [0.03, 0.06, 0.06, 0.02]), "Holm adjustment is computed correctly on a known example")
tiny = core.run_stats(core.filter_df(df, core.Selection(years=(2000, 2000), countries=("Iraq",))))
check(all(isinstance(r, core.TestResult) for r in tiny), "statistics degrade gracefully on a tiny selection", ", ".join(f"{r.key}:{'ok' if r.ok else 'skipped'}" for r in tiny))

# --------------------------------------------------------------------------------------
print("\n== 6. The Streamlit app itself (headless) ==")
try:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=120).run()
    check(not at.exception, "app starts and renders the Overview without exceptions")
    for view in ("Incidents", "Groups", "Regions", "Trends", "Human Impact", "Analysis", "Data & Methods", "Overview"):
        at.radio(key="nav").set_value(view).run()
        check(not at.exception, f"view renders: {view}")
    at.session_state["f_regions"] = ["South Asia"]
    at.run()
    check(not at.exception, "region filter applies without exceptions")
    at.session_state["f_attacks"] = ["Hijacking"]
    at.session_state["f_targets"] = ["Telecommunication"]
    at.session_state["f_years"] = (2000, 2000)
    at.run()
    check(not at.exception, "an empty selection shows the empty state without exceptions")
    for view in ("Incidents", "Groups", "Regions", "Trends", "Human Impact", "Analysis", "Data & Methods"):
        at.radio(key="nav").set_value(view).run()
        check(not at.exception, f"empty selection is safe in view: {view}")
except Exception as exc:  # pragma: no cover
    check(False, "Streamlit AppTest could not run", repr(exc))

failed = [n for ok, n in RESULTS if not ok]
print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed" + ("" if not failed else f"; FAILED: {failed}"))
sys.exit(1 if failed else 0)

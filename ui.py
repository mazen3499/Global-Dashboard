"""Streamlit plumbing shared by app.py and the pages in views/: cached data access, the page context, panels."""
from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass

import numpy as np
import streamlit as st

import charts
import core
import theme

log = logging.getLogger("gtd")


# --------------------------------------------------------------------------------------
# data access (cached)
# --------------------------------------------------------------------------------------
@st.cache_resource(show_spinner="Loading the dataset...")
def get_df():
    return core.load_data()


@st.cache_data(show_spinner=False)
def filter_options() -> dict:
    df = get_df()
    pairs = df[["region_txt", "country_txt"]].astype(str).drop_duplicates()
    groups = df.loc[df["group_named"], "gname"].astype(str).value_counts()
    return {
        "regions": sorted(pairs["region_txt"].unique()),
        "countries_by_region": {r: sorted(g["country_txt"].unique()) for r, g in pairs.groupby("region_txt")},
        "groups": list(groups.index),   # most active first, so the dropdown starts with the groups people look for
        "attacks": sorted(df["attacktype1_txt"].astype(str).unique()),
        "targets": sorted(df["targtype1_txt"].astype(str).unique()),
        "years": (int(df["iyear"].min()), int(df["iyear"].max())),
    }


@st.cache_data(show_spinner=False, max_entries=64)
def rows_for(sel: core.Selection):
    """Row positions of the selection: the mask is built once per selection, every page slices with it."""
    return core.row_positions(get_df(), sel)


def selected(sel: core.Selection):
    return get_df().iloc[rows_for(sel)]


@st.cache_data(show_spinner=False, max_entries=64)
def common(sel: core.Selection):
    fdf = selected(sel)
    return core.kpis(fdf), core.yearly(fdf, sel.years)


@st.cache_data(show_spinner=False, max_entries=64)
def changes(sel: core.Selection, data_years: tuple[int, int]) -> tuple[str, dict]:
    """Caption and percentage change of each headline figure against the earlier period (see core.comparison)."""
    c = core.comparison(sel, data_years)
    if c.previous is None:
        return c.caption, {}
    cur, prev = common(c.current)[0], common(c.previous)[0]
    fields = ("incidents", "groups", "casualties", "fatalities", "injuries")
    return c.caption, {f: core.pct_change(getattr(cur, f), getattr(prev, f)) for f in fields}


@st.cache_data(show_spinner=False, max_entries=256)
def agg(name: str, sel: core.Selection, *args):
    """Any core aggregate of the selection, cached per (aggregate, selection, arguments)."""
    return getattr(core, name)(selected(sel), *args)


@st.cache_data(show_spinner=False, max_entries=64)
def insights_for(sel: core.Selection, data_years: tuple[int, int]) -> dict:
    caption, deltas = changes(sel, data_years)
    return core.insights(selected(sel), common(sel)[1], deltas.get("incidents"), caption)


# --------------------------------------------------------------------------------------
# page context
# --------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Ctx:
    sel: core.Selection
    kp: core.Kpis
    yr: object          # pandas DataFrame, one row per selected year
    pal: dict
    mode: str
    caption: str        # what the change badges compare
    deltas: dict
    data_years: tuple[int, int]

    def agg(self, name: str, *args):
        return agg(name, self.sel, *args)

    @property
    def insights(self) -> dict:
        return insights_for(self.sel, self.data_years)

    def insight(self, key: str) -> dict | None:
        """One finding for a panel subtitle (None when the selection does not support it)."""
        return self.insights.get(key)


# --------------------------------------------------------------------------------------
# panels
# --------------------------------------------------------------------------------------
def handle_chart_click(key: str, event, fig) -> bool:
    if event is None:
        return False
    sel = getattr(event, "selection", None)
    if not sel:
        return False
    points = getattr(sel, "points", None)
    if not points:
        if f"_last_sig_{key}" in st.session_state:
            st.session_state[f"_last_sig_{key}"] = None
        return False

    sig = (key, tuple((p.get("curve_number"), p.get("point_number"), p.get("x"), p.get("y"), str(p.get("customdata"))) for p in points))
    if st.session_state.get(f"_last_sig_{key}") == sig:
        return False
    st.session_state[f"_last_sig_{key}"] = sig

    pt = points[0]
    opts = filter_options()
    all_countries = sorted({c for cs in opts["countries_by_region"].values() for c in cs})
    years_range = opts["years"]
    ss = st.session_state

    def resolve(val, valid_list: list[str]) -> str | None:
        if val is None:
            return None
        v = str(val).strip()
        for item in valid_list:
            if item.lower() == v.lower():
                return item
        for item in valid_list:
            if charts.short(item, 26).lower() == v.lower() or charts.short(item, 18).lower() == v.lower():
                return item
        return None

    def get_cd(p):
        cd = p.get("customdata")
        if isinstance(cd, (list, tuple, np.ndarray)) and len(cd) > 0:
            return cd[0]
        return cd

    applied = False

    # 1. Map charts (ov_map, r_map) & Scatter (r_scatter)
    if key in ("ov_map", "r_map", "r_scatter"):
        country = None
        cd = get_cd(pt)
        if cd and str(cd) in all_countries:
            country = str(cd)
        elif "curve_number" in pt and pt["curve_number"] is not None:
            cn = pt["curve_number"]
            if cn < len(fig.data) and fig.data[cn].name in all_countries:
                country = fig.data[cn].name
        if not country and "text" in pt:
            txt = str(pt["text"])
            if "<b>" in txt:
                cand = txt.split("<b>")[1].split("</b>")[0].strip()
                country = resolve(cand, all_countries)

        if country:
            if ss.get("f_countries") == [country]:
                ss.f_countries = []
                ss.toast_msg = f"Cleared country filter: {country}"
            else:
                ss.f_countries = [country]
                ss.f_regions = []
                ss.toast_msg = f"Filtered to country: {country}"
            ss.rec_page = 1
            applied = True

    # 2. Year charts (ov_time, t_combo, t_rates, h_year, g_attr_year)
    elif key in ("ov_time", "t_combo", "t_rates", "h_year", "g_attr_year"):
        x = pt.get("x")
        if x is not None:
            try:
                year = int(round(float(x)))
                if years_range[0] <= year <= years_range[1]:
                    if tuple(ss.get("f_years", ())) == (year, year):
                        ss.f_years = years_range
                        ss.toast_msg = f"Reset year range to {years_range[0]}–{years_range[1]}"
                    else:
                        ss.f_years = (year, year)
                        ss.toast_msg = f"Filtered to year: {year}"
                    ss.rec_page = 1
                    applied = True
            except (ValueError, TypeError):
                pass

    # 3. Region chart (r_regions)
    elif key == "r_regions":
        cd = get_cd(pt)
        region = resolve(cd, opts["regions"]) or resolve(pt.get("y"), opts["regions"])
        if region:
            if ss.get("f_regions") == [region]:
                ss.f_regions = []
                ss.toast_msg = f"Cleared region filter: {region}"
            else:
                ss.f_regions = [region]
                ss.f_countries = []
                ss.toast_msg = f"Filtered to region: {region}"
            ss.rec_page = 1
            applied = True

    # 4. Attack type charts (i_attack, h_attack, s_means)
    elif key in ("i_attack", "h_attack", "s_means"):
        cd = get_cd(pt)
        attack = resolve(cd, opts["attacks"]) or resolve(pt.get("y"), opts["attacks"])
        if attack:
            if ss.get("f_attacks") == [attack]:
                ss.f_attacks = []
                ss.toast_msg = f"Cleared attack filter: {attack}"
            else:
                ss.f_attacks = [attack]
                ss.toast_msg = f"Filtered to attack type: {attack}"
            ss.rec_page = 1
            applied = True

    # 5. Target type chart (i_target)
    elif key == "i_target":
        cd = get_cd(pt)
        target = resolve(cd, opts["targets"]) or resolve(pt.get("y"), opts["targets"])
        if target:
            if ss.get("f_targets") == [target]:
                ss.f_targets = []
                ss.toast_msg = f"Cleared target filter: {target}"
            else:
                ss.f_targets = [target]
                ss.toast_msg = f"Filtered to target type: {target}"
            ss.rec_page = 1
            applied = True

    # 6. Attack x Target Matrix (i_matrix)
    elif key == "i_matrix":
        cd = pt.get("customdata")
        attack, target = None, None
        if isinstance(cd, (list, tuple)) and len(cd) >= 2:
            attack = resolve(cd[0], opts["attacks"])
            target = resolve(cd[1], opts["targets"])
        if not attack or not target:
            attack = resolve(pt.get("y"), opts["attacks"])
            target = resolve(pt.get("x"), opts["targets"])
        if attack and target:
            ss.f_attacks = [attack]
            ss.f_targets = [target]
            ss.toast_msg = f"Filtered to {attack} on {target}"
            ss.rec_page = 1
            applied = True

    # 7. Group charts (g_years)
    elif key == "g_years":
        cd = get_cd(pt)
        group = resolve(cd, opts["groups"])
        if not group and "curve_number" in pt and pt["curve_number"] is not None:
            cn = pt["curve_number"]
            if cn < len(fig.data):
                group = resolve(fig.data[cn].name, opts["groups"])
        if group:
            if ss.get("f_groups") == [group]:
                ss.f_groups = []
                ss.toast_msg = f"Cleared group filter: {group}"
            else:
                ss.f_groups = [group]
                ss.toast_msg = f"Filtered to group: {group}"
            ss.rec_page = 1
            applied = True

    # 8. Stack share (t_mix)
    elif key == "t_mix":
        cd = get_cd(pt)
        attack = resolve(cd, opts["attacks"])
        if attack:
            if ss.get("f_attacks") == [attack]:
                ss.f_attacks = []
                ss.toast_msg = f"Cleared attack filter: {attack}"
            else:
                ss.f_attacks = [attack]
                ss.toast_msg = f"Filtered to attack type: {attack}"
            ss.rec_page = 1
            applied = True

    if applied:
        st.rerun()
    return applied


def plot(fig, key: str, cfg=charts.CFG):
    event = st.plotly_chart(fig, key=key, width="stretch", height="stretch", config=cfg, theme=None,
                            on_select="rerun", selection_mode="points")
    handle_chart_click(key, event, fig)


@contextmanager
def guarded(what: str):
    """Error boundary: a failure inside one panel is logged and shown in that panel; the rest of the page still renders."""
    try:
        yield
    except Exception:   # Streamlit's stop/rerun signals are BaseException and pass through
        log.exception("Panel failed: %s", what)
        st.html(theme.error_html(what))


@contextmanager
def panel(key: str, title: str, info: str = "", subtitle: str = "", right: str = "", insight: dict | None = None):
    with st.container(key=f"p_{key}", height="stretch"):
        st.html(theme.panel_header(title, info, subtitle, right, insight))
        with guarded(title):
            yield


@contextmanager
def panel_with_control(key: str, title: str, info: str = "", subtitle: str = "", ratio: tuple[float, float] = (3, 2),
                       insight: dict | None = None):
    """A panel whose header holds a widget on the right; yields (header column for the widget, body context)."""
    with st.container(key=f"p_{key}", height="stretch"):
        with st.container(key=f"phdr_{key}"):
            a, b = st.columns(list(ratio), vertical_alignment="center")
            with a:
                st.html(theme.panel_header(title, info, subtitle, insight=insight))
        with guarded(title):
            yield b


def ranked_note(n_unknown: int) -> str:
    return f"Unknown ({n_unknown:,} incidents) stays in every total but is not ranked." if n_unknown else ""

"""AEGIS: Global Terrorism Analysis dashboard.

Run with:  streamlit run app.py
Every number on screen is computed from the dataset (30 analysis columns) with pandas; see core.data_path.
This module is the shell (sidebar navigation, header, KPI cards, filters); the pages live in views/.
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

import core
import theme
import ui
from theme import fmt_int, fmt_share
from views import PAGES

ICON = Path(__file__).parent / "assets" / "favicon.png"
st.set_page_config(page_title="AEGIS · Global Terrorism Dashboard", page_icon=str(ICON) if ICON.exists() else None,
                   layout="wide", initial_sidebar_state="auto")

FOOTER = ("Reported totals only: unknown counts are never treated as zero.  Source: Global Terrorism Database (2000-2017), "
          "cleaned project dataset.  Rankings leave Unknown out; totals keep it.")
FOOTER_STATS = ("Exploratory results: incidents cluster by country, year and group, so p-values assume more independence than "
                "the data has.  Effect sizes live on different scales and are not comparable across tests.")
NOTES = """
**Data notes**

- **2012 collection change.** GTD changed how incidents were collected around 2012, so the rise after 2011 mixes real
  change with better coverage.
- **Unknown counts are not zero.** Totals add up valid counts only; coverage is shown on Data & Methods.
- **Success** is GTD's tactical-success flag (the attack took place), not a mission outcome.
- **9/11** is recorded as separate incidents; their fatalities are split, not duplicated.
"""
FILTER_KEYS = ("f_years", "f_regions", "f_countries", "f_groups", "f_attacks", "f_targets")

try:
    df = ui.get_df()
except core.DataError as exc:
    st.error(str(exc))
    st.stop()

opts = ui.filter_options()
YEARS = opts["years"]
ALL_COUNTRIES = sorted({c for cs in opts["countries_by_region"].values() for c in cs})
ss = st.session_state

# --------------------------------------------------------------------------------------
# session state (page and theme also live in the URL, so a link reopens the same view)
# --------------------------------------------------------------------------------------
if "booted" not in ss:
    ss.booted = True
    qp = st.query_params
    ss.nav = qp.get("page") if qp.get("page") in PAGES else "Overview"
    ss.mode = "light" if qp.get("theme") == "light" else "dark"
    if "years" in qp:
        try:
            parts = [int(p) for p in str(qp.get("years")).split("-")]
            if len(parts) == 2 and YEARS[0] <= parts[0] <= parts[1] <= YEARS[1]:
                ss.f_years = (parts[0], parts[1])
        except (ValueError, TypeError):
            pass
    if "region" in qp:
        ss.f_regions = [r for r in qp.get_all("region") if r in opts["regions"]]
    if "country" in qp:
        ss.f_countries = [c for c in qp.get_all("country") if c in ALL_COUNTRIES]
    if "group" in qp:
        ss.f_groups = [g for g in qp.get_all("group") if g in opts["groups"]]
    if "attack" in qp:
        ss.f_attacks = [a for a in qp.get_all("attack") if a in opts["attacks"]]
    if "target" in qp:
        ss.f_targets = [t for t in qp.get_all("target") if t in opts["targets"]]
DEFAULTS = {"f_years": YEARS, "f_regions": [], "f_countries": [], "f_groups": [], "f_attacks": [], "f_targets": [],
            "seg_metric": "Incidents", "q": "", "rec_query": "", "rec_sort": "Deadliest first", "rec_page": 1}
for _k, _v in DEFAULTS.items():
    ss.setdefault(_k, list(_v) if isinstance(_v, list) else _v)
ss.setdefault("seg_theme", ss.mode.title())


def reset_filters():
    for key in FILTER_KEYS:
        ss[key] = list(DEFAULTS[key]) if isinstance(DEFAULTS[key], list) else DEFAULTS[key]
    ss.rec_query, ss.q, ss.rec_page = "", "", 1


def enable_all_filters():
    ss.f_regions = ["Middle East & North Africa"]
    ss.f_countries = ["Iraq"]
    ss.f_groups = ["Islamic State of Iraq and the Levant (ISIL)"]
    ss.f_attacks = ["Bombing/Explosion"]
    ss.f_targets = ["Private Citizens & Property"]
    ss.f_years = (2014, 2016)
    ss.rec_page = 1
    ss.toast_msg = "Enabled all 6 filters: ISIL in Iraq (2014-2016)"


def set_years(years: tuple[int, int]):
    ss.f_years = years
    ss.rec_page = 1


def set_mode():
    ss.mode = ss.seg_theme.lower()


def apply_search():
    """Search box: a year, country, region, group, attack type or target type becomes a filter; anything else searches the incident records."""
    q = ss.q.strip()
    if not q:
        return
    ql = q.lower()

    if q.isdigit() and len(q) == 4:
        yr = int(q)
        if YEARS[0] <= yr <= YEARS[1]:
            if tuple(ss.f_years) == (yr, yr):
                ss.f_years = YEARS
                ss.toast_msg = f"Reset year range to {YEARS[0]}–{YEARS[1]}"
            else:
                ss.f_years = (yr, yr)
                ss.toast_msg = f"Filtered to year: {yr}"
            ss.q, ss.rec_page = "", 1
            return

    def match(names: list[str]) -> str | None:
        exact = [n for n in names if n.lower() == ql]
        part = [n for n in names if ql in n.lower()]
        return exact[0] if exact else part[0] if len(part) == 1 else None

    for key, names, what in (
        ("f_countries", ALL_COUNTRIES, "country"),
        ("f_regions", opts["regions"], "region"),
        ("f_groups", opts["groups"], "group"),
        ("f_attacks", opts["attacks"], "attack type"),
        ("f_targets", opts["targets"], "target type"),
    ):
        hit = match(names)
        if hit:
            if key == "f_countries":
                ss.f_regions = []
            if ss.get(key) == [hit]:
                ss[key] = []
                ss.toast_msg = f"Cleared {what} filter: {hit}"
            else:
                ss[key] = [hit]
                ss.toast_msg = f"Filtered to {what}: {hit}"
            ss.q, ss.rec_page = "", 1
            return
    ss.rec_query, ss.rec_page, ss.nav = q, 1, "Incidents"
    ss.toast_msg = f'Showing incidents matching "{q}"'


def country_options(regions: tuple[str, ...]) -> list[str]:
    by = opts["countries_by_region"]
    return sorted({c for r in (regions or by.keys()) for c in by.get(r, [])})


_allowed = set(country_options(tuple(ss.f_regions)))
_dropped = [c for c in ss.f_countries if c not in _allowed]
if _dropped:
    ss.f_countries = [c for c in ss.f_countries if c in _allowed]
    st.toast(f"Removed {', '.join(_dropped)} from the country filter: not in the selected region"
             if len(_dropped) <= 3 else f"Removed {len(_dropped)} countries from the country filter: not in the selected region")
if "toast_msg" in ss:
    st.toast(ss.pop("toast_msg"))

sel = core.Selection(years=tuple(ss.f_years), regions=tuple(sorted(ss.f_regions)), countries=tuple(sorted(ss.f_countries)),
                     attacks=tuple(sorted(ss.f_attacks)), targets=tuple(sorted(ss.f_targets)), groups=tuple(sorted(ss.f_groups)))
n_active = sel.n_active(YEARS)
kp, yr = ui.common(sel)
caption, deltas = ui.changes(sel, YEARS)
page, mode = ss.nav, ss.mode
pal = theme.palette(mode)
qp_params = {"page": page, "theme": mode}
if tuple(ss.f_years) != YEARS:
    qp_params["years"] = f"{ss.f_years[0]}-{ss.f_years[1]}"
if ss.f_regions:
    qp_params["region"] = list(ss.f_regions)
if ss.f_countries:
    qp_params["country"] = list(ss.f_countries)
if ss.f_groups:
    qp_params["group"] = list(ss.f_groups)
if ss.f_attacks:
    qp_params["attack"] = list(ss.f_attacks)
if ss.f_targets:
    qp_params["target"] = list(ss.f_targets)
st.query_params.clear()
st.query_params.update(qp_params)

st.html(theme.css_block(page, mode))
# Keyboard shortcuts (Ctrl+K) & cross-filtering click bridge from HTML cards to filters
st.iframe("""<script>
const d = window.parent.document;
if (!d.__aegisSearchKey) { d.__aegisSearchKey = true;
  d.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    const i = d.querySelector('.st-key-q input'); if (i) { e.preventDefault(); i.focus(); } } }); }
if (!d.__aegisCardClick) { d.__aegisCardClick = true;
  d.addEventListener('click', e => {
    const target = e.target.closest('[data-filter-val]');
    if (!target) return;
    const val = target.getAttribute('data-filter-val');
    if (!val || val === 'Other' || val === 'Unknown' || val.startsWith('Other (')) return;
    const input = d.querySelector('.st-key-q input');
    if (input) {
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(input, val);
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }
  }); }
</script>""", height=1)

# --------------------------------------------------------------------------------------
# sidebar: brand and navigation
# --------------------------------------------------------------------------------------
with st.sidebar:
    st.html(theme.brand_html())
    st.radio("Page", list(PAGES), key="nav", label_visibility="collapsed")

# --------------------------------------------------------------------------------------
# header: title, search, data notes, settings, period
# --------------------------------------------------------------------------------------
with st.container(key="hdr"):
    t, s, b1, b2, d = st.columns([5.4, 3.3, 0.45, 0.45, 1.55], vertical_alignment="center")
    with t:
        st.html(theme.title_html("Global Terrorism Analysis", "A data-driven assessment of terrorist incidents, groups, and "
                                 f"their global impact ({YEARS[0]} – {YEARS[1]})."))
    with s:
        st.text_input("Search", key="q", placeholder="Search country, group, or incident…", label_visibility="collapsed",
                      on_change=apply_search)
    with b1, st.container(key="pop_bell"):
        with st.popover("", icon=":material/notifications:", help="Data notes"):
            st.markdown(NOTES)
    with b2, st.container(key="pop_gear"):
        with st.popover("", icon=":material/settings:", help="Settings"):
            st.markdown("**Appearance**")
            st.radio("Theme", ["Dark", "Light"], key="seg_theme", horizontal=True, on_change=set_mode, label_visibility="collapsed")
            st.caption("The page and theme are kept in the address bar, so a copied link opens the same view.")
    with d:
        with st.container(key="pop_date"):
            label = f"{sel.years[0]}" if sel.years[0] == sel.years[1] else f"{sel.years[0]} – {sel.years[1]}"
            with st.popover(label, icon=":material/calendar_month:", width="stretch"):
                st.markdown("**Period**")
                last5 = (YEARS[1] - 4, YEARS[1])
                for text, years in ((f"All years ({YEARS[0]} – {YEARS[1]})", YEARS),
                                    (f"Last five years ({last5[0]} – {last5[1]})", last5),
                                    (f"Since the 2012 collection change (2012 – {YEARS[1]})", (2012, YEARS[1])),
                                    (f"Before 2012 ({YEARS[0]} – 2011)", (YEARS[0], 2011))):
                    st.button(text, key=f"yr_{years[0]}_{years[1]}", on_click=set_years, args=(years,), width="stretch",
                              disabled=tuple(sel.years) == years)
                st.caption("Any other range: Year Range in Filters.")

# --------------------------------------------------------------------------------------
# KPI cards
# --------------------------------------------------------------------------------------
cov = f"fatalities reported for {fmt_share(kp.fatalities_cov)} of incidents, injuries for {fmt_share(kp.injuries_cov)}"
st.html(theme.kpi_cards([
    {"icon": "target", "value": fmt_int(kp.incidents), "label": "Total Incidents", "delta": deltas.get("incidents"),
     "caption": caption, "tip": "Unique incidents (eventid) in the selection"},
    {"icon": "people", "value": fmt_int(kp.groups), "label": "Terrorist Groups", "delta": deltas.get("groups"), "caption": caption,
     "indigo": True, "tip": "Distinct named perpetrator groups (Unknown excluded)"},
    {"icon": "casualties", "value": fmt_int(kp.casualties), "label": "Total Casualties", "delta": deltas.get("casualties"),
     "caption": caption, "tip": f"Reported fatalities plus reported injuries; {cov}"},
    {"icon": "fatalities", "value": fmt_int(kp.fatalities), "label": "Fatalities", "delta": deltas.get("fatalities"), "caption": caption,
     "tip": f"Reported fatalities (valid counts); fatalities reported for {fmt_share(kp.fatalities_cov)} of incidents"},
]))

# --------------------------------------------------------------------------------------
# body: filters card + page
# --------------------------------------------------------------------------------------
with st.container(key="body"):
    fcol, pcol = st.columns([15.5, 84.5])
    with fcol:
        with st.container(key="p_filters", height="stretch"):
            a, b = st.columns([1.4, 2.6], vertical_alignment="center")
            with a:
                st.html('<div class="pt">Filters</div>')
            with b:
                b1, b2 = st.columns([1.1, 0.9], vertical_alignment="center")
                with b1:
                    st.button("Enable All", type="tertiary", key="enable_all", on_click=enable_all_filters,
                              help="Enable all 6 filters with a verified benchmark scenario")
                with b2:
                    st.button("Reset", type="tertiary", key="reset", on_click=reset_filters,
                              disabled=n_active == 0 and not ss.rec_query)
            st.multiselect("Region", opts["regions"], key="f_regions", placeholder="All Regions",
                           on_change=lambda: ss.update(rec_page=1))
            st.multiselect("Country", country_options(tuple(ss.f_regions)), key="f_countries", placeholder="All Countries",
                           on_change=lambda: ss.update(rec_page=1))
            st.multiselect("Terrorist Group", opts["groups"], key="f_groups", placeholder="All Groups",
                           on_change=lambda: ss.update(rec_page=1))
            st.multiselect("Attack Type", opts["attacks"], key="f_attacks", placeholder="All Types",
                           on_change=lambda: ss.update(rec_page=1))
            st.multiselect("Target Type", opts["targets"], key="f_targets", placeholder="All Targets",
                           on_change=lambda: ss.update(rec_page=1))
            st.slider("Year Range", YEARS[0], YEARS[1], key="f_years",
                      on_change=lambda: ss.update(rec_page=1))
            st.button("Apply Filters", type="primary", icon=":material/filter_alt:", width="stretch",
                      key="apply_filters", on_click=lambda: ss.update(rec_page=1))
            st.html(f'<div class="fl-note">{n_active} filter{"s" if n_active != 1 else ""} active · '
                    f'{fmt_int(kp.incidents)} of {fmt_int(len(df))} incidents</div>')
    with pcol:
        if kp.incidents == 0:
            with st.container(key="p_empty", height="stretch"):
                st.html(theme.empty_html("Widen the year range or clear one of the filters, then Apply. Reset starts over."))
        else:
            PAGES[page](ui.Ctx(sel=sel, kp=kp, yr=yr, pal=pal, mode=mode, caption=caption, deltas=deltas, data_years=YEARS))

st.html(theme.footer_html(FOOTER_STATS if page == "Analysis" else FOOTER))

"""Data & Methods: definitions, coverage, reconciliation with the notebook and Power BI, and the data download."""
from __future__ import annotations

import streamlit as st

import charts
import core
import theme
import ui
from theme import fmt_int

DEFINITIONS = [
    ("Incidents", "Unique eventid values in the selection (one GTD record per incident)."),
    ("Reported fatalities and injuries", "Sums of valid counts: present, not negative and a whole number. Unknown or invalid "
     "counts are left out and never treated as zero, so totals are lower bounds."),
    ("Total casualties", "Reported fatalities plus reported injuries."),
    ("Terrorist groups", "Distinct named perpetrator groups (gname other than Unknown)."),
    ("Change badges", "The selected period against the equal period just before it; when the data does not reach back that "
     "far, the last selected year against the year before. Increases in harm show red, decreases green."),
    ("Success", "GTD's tactical-success flag (the attack took place), not a mission outcome."),
    ("Rankings", "Unknown labels stay in every total but are left out of Top-N rankings; each ranking says how many."),
    ("Map", "Countries on the Natural Earth 1:110m map; places without a polygon at that scale are drawn as dots."),
    ("2012 collection change", "GTD changed how incidents were collected around 2012; counts before and after are not "
     "strictly comparable."),
    ("Statistics", "Exploratory: incidents cluster by country, year and group, so p-values assume more independence than "
     "the data has. Holm adjustment across the four tests."),
]


def render(ctx: ui.Ctx) -> None:
    pal = ctx.pal
    with st.container(key="row_a"):
        c1, c2, c3 = st.columns([36, 30, 34])
        with c1:
            with ui.panel("d_defs", "Definitions", "How every figure on the dashboard is counted."):
                st.html(theme.definitions_html(DEFINITIONS))
        with c2:
            with ui.panel("d_cov", "Data Coverage", "Share of incidents in the selection that carry each piece of information."):
                st.html(theme.coverage_html(ctx.agg("coverage_rows")))
        with c3:
            with ui.panel("d_recon", "Reconciliation", "The selection's totals under the counting rule of each project deliverable, "
                          "all computed here from the same data."):
                rows = [[f"<b>{r['measure']}</b>", fmt_int(r["dashboard"]), fmt_int(r["notebook"]), fmt_int(r["power_bi"]),
                         "" if r["dashboard"] == r["notebook"] == r["power_bi"] else '<span class="pill">differs</span>']
                        for r in ctx.agg("reconciliation")]
                st.html(theme.table_html([("Measure", ""), ("Dashboard", "n"), ("Notebook", "n"), ("Power BI", "n"), ("", "")], rows))
                st.html('<div class="fl-note">Dashboard: valid counts only (the two records with 8.5 injuries are invalid). '
                        'Notebook: raw sums. Power BI: injuries stored as whole numbers, so 8.5 becomes 8.</div>')
    with st.container(key="row_b"):
        c1, c2 = st.columns([58, 42])
        with c1:
            with ui.panel("d_missing", "Missing Casualty Counts by Year", "Share of each year's incidents without a valid fatality or "
                          "injury count. Where it is high, totals are low bounds."):
                ui.plot(charts.missing_fig(ctx.agg("missing_by_year", ctx.sel.years), pal), "d_missing")
        with c2:
            with ui.panel("d_source", "Source and Download", "Where the data comes from and how it was prepared."):
                path = core.data_path()
                st.html(theme.definitions_html([
                    ("Source", "Global Terrorism Database (START, University of Maryland), incidents 2000-2017, cleaned in the "
                               "project notebook (30 analysis columns, 24 engineered)."),
                    ("File read by the app", f"{path.name}: {fmt_int(len(ui.get_df()))} incidents, read once and cached."),
                    ("Validation", "validate.py recomputes every KPI, chart total and test independently; tests run in CI."),
                    ("Offline", "Maps (Natural Earth) and fonts are bundled: the app makes no external request."),
                ]))
                rec = ctx.agg("records", "", "Most recent first")
                st.download_button(f"Download the selection ({len(rec):,} incidents, CSV)", rec.to_csv(index=False).encode(),
                                   file_name="gtd_selection.csv", mime="text/csv", icon=":material/download:", key="d_csv")

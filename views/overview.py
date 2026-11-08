"""Overview: map, incidents over time, attack types, top groups, human impact and key insights."""
from __future__ import annotations

import streamlit as st

import charts
import theme
import ui
from theme import fmt_share


def render(ctx: ui.Ctx) -> None:
    kp, pal = ctx.kp, ctx.pal
    middle, right = st.columns([79, 21])
    with middle:
        with st.container(key="row_a"):
            c1, c2 = st.columns([63, 37])
            with c1:
                with ui.panel("map", "Incidents by Country",
                              "Incidents per country in the selection. Small islands and former states without a polygon "
                              "on the 1:110m map are shown as dots. Scroll to zoom, drag to pan, double-click to reset."):
                    countries = ctx.agg("country_table")
                    ui.plot(charts.choropleth_fig(countries, pal), "ov_map", charts.MAP_CFG)
                    st.html(theme.map_legend_html(charts.map_classes(countries, pal)))
            with c2:
                with ui.panel("time", "Incidents Over Time", "Recorded incidents per year in the selected period. The rise after "
                              "2011 reflects both events and a change in how GTD collected them."):
                    ui.plot(charts.area_fig(ctx.yr, pal), "ov_time")
        with st.container(key="row_b"):
            c1, c2, c3 = st.columns([38, 31, 31])
            with c1:
                with ui.panel("attack", "Attack Types", "Primary attack type. The five most common named types; "
                              "'Other' holds the rest, including Unknown."):
                    rows = [(charts.short(lab, 18), n, pct) for lab, n, pct in ctx.agg("attack_mix", 5)]
                    st.html(theme.donut_html(rows, kp.incidents, charts.series_colors(pal, len(rows)), pal["track"], size=106))
            with c2:
                ranked, n_unknown = ctx.agg("ranking", "gname")
                with ui.panel("groups", "Top Terrorist Groups", "Incidents per named perpetrator group. "
                              + ui.ranked_note(n_unknown)):
                    top = ranked.head(5)
                    st.html(theme.bars_html([(charts.short(g, 20), g, float(n), f"{int(n):,}") for g, n in top["incidents"].items()]))
            with c3:
                with ui.panel("impact", "Human Impact", "Reported casualties: valid counts only, unknown counts are never "
                              "treated as zero. Hover a tile for its coverage."):
                    st.html(theme.human_impact_html(
                        kp.injuries, kp.fatalities, ctx.deltas.get("injuries"), ctx.deltas.get("fatalities"), "",
                        f"{fmt_share(kp.injuries_cov)} of incidents report an injury count",
                        f"{fmt_share(kp.fatalities_cov)} of incidents report a fatality count"))
    with right:
        with ui.panel("insights", "Key Insights", "Computed from the current selection; each statement names its denominator."):
            items = list(ctx.insights.values())
            st.html(theme.insights_html(items, grouped=True) if items else theme.empty_html("Not enough data for insights.", ""))

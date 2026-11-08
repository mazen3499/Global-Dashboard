"""Regions: where incidents concentrate, by country, region and city (research question 2)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts
import theme
import ui
from theme import esc, fmt_num

METRICS = {"Incidents": "incidents", "Fatalities": "fatalities", "Injuries": "injuries"}


def render(ctx: ui.Ctx) -> None:
    pal = ctx.pal
    countries = ctx.agg("country_table")
    with st.container(key="row_a"):
        c1, c2 = st.columns([62, 38])
        with c1:
            metric = METRICS[st.session_state.get("seg_metric", "Incidents")]
            with ui.panel_with_control("map", "Geographic Distribution", "Countries shaded by the chosen measure (valid counts for "
                                       "fatalities and injuries). Scroll to zoom, drag to pan, double-click to reset.", ratio=(1, 1)) as ctl:
                with ctl:
                    st.radio("Map measure", list(METRICS), key="seg_metric", horizontal=True, label_visibility="collapsed")
                ui.plot(charts.choropleth_fig(countries, pal, metric), "r_map", charts.MAP_CFG)
                st.html(theme.map_legend_html(charts.map_classes(countries, pal, metric)))
        with c2:
            with ui.panel("r_countries", "Countries", "Twelve countries with the most incidents. Fatalities per incident uses "
                          "incidents with a known count."):
                top = countries.head(12)
                lethality = top["fatalities"] / top["fatal_known"].where(top["fatal_known"] > 0)
                rows = [[f'<b data-filter-val="{esc(c)}" style="cursor:pointer" title="{esc(c)}: {r.share:.1f}% of incidents">{esc(charts.short(c, 18))}</b>', f"{int(r.incidents):,}",
                         "&ndash;" if pd.isna(r.fatalities) else f"{int(r.fatalities):,}", fmt_num(lethality[c])]
                        for c, r in top.iterrows()]
                st.html(theme.table_html([("Country", "w"), ("Incidents", "n"), ("Killed", "n"), ("Per inc.", "n")], rows))
    with st.container(key="row_b"):
        c1, c2, c3 = st.columns([38, 28, 34])
        with c1:
            with ui.panel("r_regions", "Regions", "Incidents and reported fatalities for every region in the selection."):
                ui.plot(charts.dual_hbar_fig(ctx.agg("entity_table", "region_txt"), pal, label_len=22), "r_regions")
        with c2:
            cities, n_unknown = ctx.agg("city_table", 8)
            with ui.panel("r_cities", "Top Cities", f"Incidents per named city. {n_unknown:,} incidents with an unknown city "
                          "are not ranked."):
                st.html(theme.bars_html([(charts.short(c, 22), c, float(n), f"{int(n):,}") for c, n in cities["incidents"].items()]))
        with c3:
            with ui.panel("r_scatter", "Volume versus Lethality", "Each dot is a country with 15 or more incidents reporting a "
                          "fatality count. Dotted lines mark 1 and 10 fatalities per incident."):
                ui.plot(charts.lethality_scatter_fig(countries, pal), "r_scatter")

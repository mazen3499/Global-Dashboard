"""Trends: how frequency, lethality, method and outcome changed over time (research question 1)."""
from __future__ import annotations

import streamlit as st

import charts
import ui


def render(ctx: ui.Ctx) -> None:
    pal = ctx.pal
    with st.container(key="row_a"):
        c1, c2 = st.columns([62, 38])
        with c1:
            with ui.panel("t_combo", "Incidents and Fatalities by Year", "Incidents (line, left axis) and reported fatalities "
                          "(bars, right axis). The dotted line marks the 2012 change in GTD collection methods."):
                ui.plot(charts.trend_combo_fig(ctx.yr, pal), "t_combo")
        with c2:
            with ui.panel("t_month", "Incidents by Month", "Incidents per calendar month across the selected years; the busiest "
                          "month is highlighted."):
                ui.plot(charts.month_fig(ctx.agg("month_table"), pal), "t_month")
    with st.container(key="row_b"):
        c1, c2 = st.columns([55, 45])
        with c1:
            with ui.panel("t_mix", "Attack Type Mix by Year", "Share of each year's incidents by primary attack type: the five most "
                          "common named types, then Other (Unknown included)."):
                ui.plot(charts.stack_share_fig(ctx.agg("attack_mix_by_year", ctx.sel.years, 5), pal), "t_mix")
        with c2:
            rates = ctx.agg("rates_by_year", ctx.sel.years).rename(columns={"success_pct": "Success rate", "suicide_pct": "Suicide attacks"})
            with ui.panel("t_rates", "Success and Suicide Rates", "Success: incidents flagged success = 1 among those with a known "
                          "flag (GTD's tactical success, not a mission outcome). Suicide: share of incidents flagged as suicide attacks."):
                ui.plot(charts.lines_fig(rates, pal, [pal["green"], pal["red"]], suffix="%", y_range=[0, 100]), "t_rates")

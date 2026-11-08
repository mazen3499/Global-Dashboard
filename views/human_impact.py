"""Human impact: reported fatalities and injuries, how concentrated they are, and suicide versus other attacks."""
from __future__ import annotations

import streamlit as st

import charts
import theme
import ui
from theme import fmt_share


def render(ctx: ui.Ctx) -> None:
    pal, kp = ctx.pal, ctx.kp
    cov = f"Fatalities reported for {fmt_share(kp.fatalities_cov)} of incidents, injuries for {fmt_share(kp.injuries_cov)}"
    with st.container(key="row_a"):
        c1, c2 = st.columns([58, 42])
        with c1:
            with ui.panel("h_year", "Fatalities and Injuries by Year", "Valid counts only; unknown counts are never treated as zero, "
                          "so these totals are lower bounds.", subtitle=cov):
                ui.plot(charts.casualties_year_fig(ctx.yr, pal), "h_year")
        with c2:
            with ui.panel("h_dist", "How Deadly Is a Typical Incident?", "Share of incidents and share of reported fatalities in "
                          "each fatality band (incidents with a known count)."):
                ui.plot(charts.fatality_dist_fig(ctx.agg("fatality_buckets"), pal), "h_dist")
    with st.container(key="row_b"):
        c1, c2 = st.columns([55, 45])
        with c1:
            by_attack = ctx.agg("casualties_by_attack")
            with ui.panel("h_attack", "Casualties by Attack Type", "Reported fatalities and injuries for the seven attack types with "
                          "the most casualties."):
                if len(by_attack):
                    ui.plot(charts.casualties_attack_fig(by_attack, pal), "h_attack")
                else:
                    st.html(theme.empty_html("No reported casualties in this selection.", ""))
        with c2:
            with ui.panel("h_suicide", "Suicide and Other Attacks", "Means and medians of valid counts; see Analysis for the "
                          "Mann-Whitney test."):
                st.html(theme.compare_html(ctx.agg("suicide_compare")))

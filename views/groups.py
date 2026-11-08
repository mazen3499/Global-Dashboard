"""Groups: who is responsible, how activity changed, how much is unattributed (research question 4)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import charts
import theme
import ui
from theme import esc, fmt_num


def render(ctx: ui.Ctx) -> None:
    pal, kp = ctx.pal, ctx.kp
    ranked, n_unknown = ctx.agg("ranking", "gname")
    with st.container(key="row_a"):
        c1, c2 = st.columns([40, 60])
        with c1:
            with ui.panel("g_top", "Top Terrorist Groups", "Incidents per named group, ten largest. " + ui.ranked_note(n_unknown),
                          subtitle=f"{kp.groups:,} named groups in the selection"):
                top = ranked.head(10)
                st.html(theme.bars_html([(charts.short(g, 24), g, float(n), f"{int(n):,}") for g, n in top["incidents"].items()]))
        with c2:
            by_year = ctx.agg("groups_by_year", ctx.sel.years, 5)
            with ui.panel("g_years", "Top 5 Groups by Year", "Incidents per year for the five largest named groups in the selection."):
                if by_year.shape[1]:
                    ui.plot(charts.lines_fig(by_year, pal, charts.series_colors(pal, by_year.shape[1]), label_len=20), "g_years")
                else:
                    st.html(theme.empty_html("No named group in this selection.", ""))
    with st.container(key="row_b"):
        c1, c2, c3 = st.columns([30, 32, 38])
        with c1:
            with ui.panel("g_attr", "Attribution", "Incidents with a named perpetrator group versus Unknown."):
                named = kp.incidents - n_unknown
                rows = [("Named group", named, 100 * named / kp.incidents), ("Unattributed", n_unknown, 100 * n_unknown / kp.incidents)]
                st.html(theme.donut_html(rows, kp.incidents, [pal["indigo"], pal["red"]], pal["track"], size=118))
        with c2:
            attr = ctx.agg("attribution_by_year", ctx.sel.years)
            with ui.panel("g_attr_year", "Attribution and Claims by Year", "Share of incidents with a named group, and the share "
                          "of those for which responsibility was claimed (incidents with a known claim flag)."):
                t = attr.rename(columns={"attributed_pct": "Named group", "claimed_pct": "Claimed (of named)"})
                ui.plot(charts.lines_fig(t, pal, [pal["indigo"], pal["red"]], suffix="%", y_range=[0, 100]), "g_attr_year")
        with c3:
            summary = ctx.agg("group_summary", 8)
            with ui.panel("g_table", "Group Profiles", "Largest named groups: incidents, reported fatalities, fatalities per incident "
                          "with a known count and years active in the selection. Hover a name for its main country."):
                rows = [[f'<b data-filter-val="{esc(g)}" style="cursor:pointer" title="{esc(g)}: most incidents in {esc(r.country)}">{esc(charts.short(g, 20))}</b>', f"{int(r.incidents):,}",
                         "&ndash;" if pd.isna(r.fatalities) else f"{int(r.fatalities):,}", fmt_num(r.lethality),
                         f"{int(r.first)}-{int(r.last)}"] for g, r in summary.iterrows()]
                st.html(theme.table_html([("Group", "w"), ("Incidents", "n"), ("Killed", "n"), ("Per inc.", "n"), ("Active", "")], rows))

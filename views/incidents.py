"""Incidents: how attacks are carried out (attack, target and weapon types) and the incident records themselves."""
from __future__ import annotations

import math

import pandas as pd
import streamlit as st

import charts
import core
import theme
import ui
from theme import esc

PAGE_SIZE = 50


def _ranked_bar(ctx: ui.Ctx, key: str, title: str, col: str, n: int) -> None:
    ranked, n_unknown = ctx.agg("ranking", col)
    with ui.panel(key, title, f"Incidents by primary {title.lower()[:-1]}. " + ui.ranked_note(n_unknown)):
        if len(ranked):
            ui.plot(charts.hbar_fig(core.with_other(ranked, n), ctx.pal, label_len=18), key)
        else:
            st.html(theme.empty_html("Only Unknown in this selection.", ""))


def _records_table(rec: pd.DataFrame) -> str:
    def num(v) -> str:
        return "<span title='not reported'>&ndash;</span>" if pd.isna(v) else f"{int(v):,}"

    rows = [[esc(r.date), f'<b data-filter-val="{esc(r.country)}" style="cursor:pointer" title="{esc(r.place)}">{esc(r.place)}</b>',
             f'<span data-filter-val="{esc(r.attack)}" style="cursor:pointer" title="{esc(r.attack)} on {esc(r.target)}">{esc(charts.short(r.attack, 16))}</span>',
             f'<span data-filter-val="{esc(r.group)}" style="cursor:pointer" title="{esc(r.group)}">{esc(charts.short(r.group, 18))}</span>', num(r.killed), num(r.injured)]
            for r in rec.itertuples()]
    cols = [("Date", ""), ("Location", "w"), ("Attack", ""), ("Group", ""), ("Killed", "n"), ("Injured", "n")]
    return theme.table_html(cols, rows)


def render(ctx: ui.Ctx) -> None:
    with st.container(key="row_a"):
        c1, c2, c3 = st.columns(3)
        with c1:
            _ranked_bar(ctx, "i_attack", "Attack Types", "attacktype1_txt", 7)
        with c2:
            _ranked_bar(ctx, "i_target", "Target Types", "targtype1_txt", 7)
        with c3:
            _ranked_bar(ctx, "i_weapon", "Weapon Types", "weaptype1_txt", 6)
    with st.container(key="row_b"):
        c1, c2 = st.columns([62, 38])
        with c1:
            query = st.session_state.get("rec_query", "")
            sort = st.session_state.get("rec_sort", "Deadliest first")
            rec = ctx.agg("records", query, sort)
            pages = max(1, math.ceil(len(rec) / PAGE_SIZE))
            page = min(st.session_state.get("rec_page", 1), pages)
            start = (page - 1) * PAGE_SIZE
            found = f"{len(rec):,} incidents" + (f' matching "{query}"' if query else "")
            with ui.panel_with_control("records", "Incident Records", "Every incident in the selection. Search with the box at "
                                       "the top (city, country, group, target or event ID). Killed and injured are valid counts; "
                                       "a dash means not reported.", subtitle=f"{found}; rows {start + 1:,}-{min(start + PAGE_SIZE, len(rec)):,}",
                                       ratio=(4, 5)) as ctl:
                with ctl:
                    a, b, c, d = st.columns([3.2, 1, 1, 2.2], vertical_alignment="center")
                    with a:
                        st.selectbox("Sort", list(core.RECORD_SORTS), key="rec_sort", label_visibility="collapsed",
                                     on_change=lambda: st.session_state.update(rec_page=1))
                    with b:
                        st.button("", icon=":material/chevron_left:", key="rec_prev", disabled=page <= 1, help="Previous page",
                                  on_click=lambda: st.session_state.update(rec_page=page - 1))
                    with c:
                        st.button("", icon=":material/chevron_right:", key="rec_next", disabled=page >= pages, help="Next page",
                                  on_click=lambda: st.session_state.update(rec_page=page + 1))
                    with d:
                        st.download_button("CSV", rec.to_csv(index=False).encode(), file_name="gtd_incidents_selection.csv",
                                           mime="text/csv", icon=":material/download:", key="rec_csv",
                                           help="Download every incident in the selection (current search and sort)")
                if query:
                    st.button(f'Clear search "{query}"', key="rec_clear", icon=":material/close:",
                              on_click=lambda: st.session_state.update(rec_query="", q="", rec_page=1))
                if len(rec):
                    st.html(_records_table(rec.iloc[start:start + PAGE_SIZE]))
                else:
                    st.html(theme.empty_html("No incident matches the search in this selection.", "No matching incidents"))
        with c2:
            matrix, excluded = ctx.agg("attack_target_matrix", 6)
            with ui.panel("i_matrix", "Attack Type by Target", f"Incident counts for the six most common target types. "
                          f"{excluded:,} incidents with an unknown attack or target type are excluded."):
                if len(matrix):
                    ui.plot(charts.heatmap_fig(matrix, ctx.pal, col_len=11), "i_matrix")
                else:
                    st.html(theme.empty_html("Not enough labelled incidents in this selection.", ""))

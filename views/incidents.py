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

    rows = []
    for r in rec.itertuples():
        date_val = getattr(r, "date", "")
        place_val = getattr(r, "place", getattr(r, "country_txt", getattr(r, "country", "")))
        country_val = getattr(
            r,
            "country",
            getattr(
                r,
                "country_txt",
                str(place_val).split(",")[-1].strip() if "," in str(place_val) else place_val,
            ),
        )
        attack_val = getattr(r, "attack", getattr(r, "attacktype1_txt", ""))
        target_val = getattr(r, "target", getattr(r, "targtype1_txt", ""))
        group_val = getattr(r, "group", getattr(r, "gname", ""))
        killed_val = getattr(r, "killed", getattr(r, "nkill", float("nan")))
        injured_val = getattr(r, "injured", getattr(r, "nwound", float("nan")))
        attack_title = f"{esc(attack_val)} on {esc(target_val)}" if target_val else esc(attack_val)

        rows.append([
            esc(date_val),
            f'<b data-filter-val="{esc(country_val)}" style="cursor:pointer" title="{esc(place_val)}">{esc(place_val)}</b>',
            f'<span data-filter-val="{esc(attack_val)}" style="cursor:pointer" title="{attack_title}">{esc(charts.short(attack_val, 16))}</span>',
            f'<span data-filter-val="{esc(group_val)}" style="cursor:pointer" title="{esc(group_val)}">{esc(charts.short(group_val, 18))}</span>',
            num(killed_val),
            num(injured_val),
        ])

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
                if len

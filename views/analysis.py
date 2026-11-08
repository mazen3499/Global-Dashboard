"""Analysis: the notebook's four hypothesis tests recomputed on the selection, with effect sizes and Holm adjustment."""
from __future__ import annotations

import streamlit as st

import charts
import core
import theme
import ui


def read_stat(r: core.TestResult) -> str:
    """One plain-language sentence for a test result."""
    d = r.detail
    if not r.ok:
        return r.note
    sig = r.p_holm is not None and r.p_holm < 0.05
    if r.key == "spearman":
        a = abs(r.effect)
        strength = "negligible" if a < 0.1 else "weak" if a < 0.3 else "moderate" if a < 0.5 else "strong"
        if a < 0.1 or not sig:
            return "No clear monotonic link between reported fatalities and reported injuries in this selection."
        direction = "more" if r.effect > 0 else "fewer"
        return (f"Incidents with more reported fatalities tend to report {direction} injuries: a {strength} "
                f"{'positive' if r.effect > 0 else 'negative'} rank correlation.")
    if r.key == "chi2":
        if not sig:
            return "No evidence that attack type and target type are linked in this selection."
        return (f"Attack type and target type are not independent: some methods concentrate on particular targets. "
                f"{d['excluded']:,} incidents with an unknown label are excluded.")
    if r.key == "mwu":
        if not sig:
            return "No clear difference in reported fatalities between suicide and other attacks in this selection."
        more = "Suicide attacks" if r.effect > 0 else "Other attacks"
        ps = d["prob_superiority"] if r.effect > 0 else 1 - d["prob_superiority"]
        return (f"{more} report more fatalities: median {d['median_a']:.0f} (suicide) vs {d['median_b']:.0f}, mean {d['mean_a']:.1f} "
                f"vs {d['mean_b']:.1f}. In a random pair, the {'suicide' if r.effect > 0 else 'other'} attack has more fatalities "
                f"about {100 * ps:.0f}% of the time (ties count half).")
    if r.key == "kw":
        if not sig:
            return "No clear difference in reported fatalities across attack types in this selection."
        return (f"Reported fatalities differ across {d['groups']} attack types. Highest mean: {charts.short(d['top_mean'])} "
                f"({d['top_mean_value']:.1f}); highest median: {charts.short(d['top_median'])} ({d['top_median_value']:.0f}). "
                "The omnibus test does not say which pairs differ.")
    return ""


def _stat_panel(ctx: ui.Ctx, r: core.TestResult) -> None:
    pal = ctx.pal
    with st.container(key=f"p_s_{r.key}", height="stretch"):
        with ui.guarded(r.name):
            left, right = st.columns([11, 9])
            with left:
                st.html(theme.stat_card_html(r, read_stat(r)))
            with right:
                if not r.ok:
                    st.html(theme.mini_header("No companion chart", "Not enough data in this selection"))
                elif r.key == "spearman":
                    st.html(theme.mini_header("Incidents by fatality and injury band", "Incidents with both counts known"))
                    ui.plot(charts.band_heatmap_fig(ctx.agg("casualty_bucket_matrix"), pal), "s_bands")
                elif r.key == "chi2":
                    pairs = [(charts.short(a, 20), charts.short(t, 20), ratio, obs) for a, t, ratio, obs in r.detail["top_pairs"]]
                    st.html(theme.pairs_html(pairs))
                elif r.key == "mwu":
                    st.html(theme.mini_header("Share of incidents by fatalities", "Suicide versus other attacks, known counts"))
                    ui.plot(charts.suicide_bands_fig(ctx.agg("suicide_buckets"), pal), "s_suicide")
                elif r.key == "kw":
                    st.html(theme.mini_header("Mean and median fatalities by attack type", "Known counts; the diamond marks the median"))
                    ui.plot(charts.attack_means_fig(ctx.agg("attack_fatality_summary"), pal), "s_means")


def render(ctx: ui.Ctx) -> None:
    tests = ctx.agg("run_stats")
    for row, pair in (("row_a", tests[:2]), ("row_b", tests[2:])):
        with st.container(key=row):
            for col, r in zip(st.columns(2), pair, strict=True):
                with col:
                    _stat_panel(ctx, r)

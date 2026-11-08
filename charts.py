"""Plotly figure builders. Every function takes already-aggregated data (see core.py) and the active palette
(theme.palette), so the same chart renders correctly in the dark and the light theme."""
from __future__ import annotations

import functools
import json
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from theme import ASSETS, FONT_SANS, SERIES

CFG = {"displayModeBar": False, "responsive": True}
MAP_CFG = {"displayModeBar": True, "displaylogo": False, "responsive": True, "scrollZoom": True, "doubleClick": "reset",
           "modeBarButtons": [["zoomIn2d", "zoomOut2d", "resetScale2d"]]}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def series_colors(pal: dict, n: int) -> list[str]:
    return [pal[SERIES[i % len(SERIES)]] for i in range(n)]


SHORT = {
    "Hostage Taking (Kidnapping)": "Hostage Taking", "Hostage Taking (Barricade Incident)": "Barricade hostage",
    "Facility/Infrastructure Attack": "Facility Attack", "Armed Assault": "Armed Assault",
    "Unarmed Assault": "Unarmed Assault", "Private Citizens & Property": "Private citizens",
    "Government (General)": "Government", "Religious Figures/Institutions": "Religious",
    "Educational Institution": "Education", "Journalists & Media": "Journalists", "Airports & Aircraft": "Aviation",
    "Government (Diplomatic)": "Diplomatic", "Terrorists/Non-State Militia": "Militia",
    "Violent Political Party": "Political party", "Food or Water Supply": "Food or water", "Abortion Related": "Abortion related",
    "Telecommunication": "Telecom", "Transportation": "Transport", "Other targets": "Other targets",
    "Vehicle (not to include vehicle-borne explosives, i.e., car or truck bombs)": "Vehicle",
    "Explosives/Bombs/Dynamite": "Explosives", "Sabotage Equipment": "Sabotage equipment",
    "West Bank and Gaza Strip": "West Bank & Gaza", "Democratic Republic of the Congo": "DR Congo",
    "Central African Republic": "C. African Rep.", "Bosnia-Herzegovina": "Bosnia-Herz.", "Serbia-Montenegro": "Serbia-Montenegro",
    "Middle East & North Africa": "Middle East & N. Africa", "Central America & Caribbean": "Central Am. & Caribbean",
    "Australasia & Oceania": "Australasia & Oceania", "Trinidad and Tobago": "Trinidad & Tobago",
    # perpetrator groups whose generic shortening (below) would read badly
    "Islamic State of Iraq and the Levant (ISIL)": "ISIL (Islamic State)",
    "Tehrik-i-Taliban Pakistan (TTP)": "Tehrik-i-Taliban (TTP)",
    "Revolutionary Armed Forces of Colombia (FARC)": "FARC",
    "Revolutionary Armed Forces of Colombia (FARC) dissidents": "FARC dissidents",
    "National Liberation Army of Colombia (ELN)": "ELN (Colombia)",
    "National Liberation Army (NLA) (Macedonia)": "NLA (Macedonia)",
    "Kurdistan Workers' Party (PKK)": "PKK (Kurdistan)",
}
_TRAILING_PAREN = re.compile(r"^(?P<base>.+?)\s*\((?P<abbr>[^()]+)\)$")


def short(label: str, n: int = 22) -> str:
    """Axis label of about ``n`` characters at most; the full label is always in the hover text.

    Order: explicit alias, the name without its trailing "(ABBR)", the abbreviation alone, then a cut at a
    word boundary (never mid-word).
    """
    s = SHORT.get(label)
    if s:
        return s
    if label.startswith("Other (") or len(label) <= n:
        return label
    m = _TRAILING_PAREN.match(label)
    if m:
        if len(m["base"]) <= n:
            return m["base"]
        if len(m["abbr"]) <= n:
            return m["abbr"]
    head = label[: n - 1]
    if " " in head and label[n - 1] != " ":
        head = head.rsplit(" ", 1)[0]
    return head.rstrip(" -,&(/") + "…"


def _num(x, d: int = 0) -> str:
    return "not reported" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:,.{d}f}"


def _base(fig: go.Figure, pal: dict, **kw) -> go.Figure:
    layout = dict(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_SANS, size=11.5, color=pal["text2"]),
        margin=dict(l=2, r=2, t=2, b=2),
        hoverlabel=dict(bgcolor=pal["hover_bg"], bordercolor=pal["line_strong"], align="left",
                        font=dict(family=FONT_SANS, size=12, color=pal["text"])),
    )
    layout.update(kw)
    fig.update_layout(**layout)
    fig.update_xaxes(automargin=True)
    fig.update_yaxes(automargin=True)
    return fig


def _legend(pal: dict, **kw) -> dict:
    return dict(orientation="h", x=0, y=1.0, xanchor="left", yanchor="bottom", font=dict(size=11, color=pal["text2"]),
                bgcolor="rgba(0,0,0,0)", **kw)


def _year_axis(x: list[int], pal: dict) -> dict:
    step = 1 if len(x) <= 7 else 2 if len(x) <= 12 else 4
    return dict(tickmode="array", tickvals=x[::step], showgrid=False, zeroline=False, fixedrange=True, tickangle=0,
                tickfont=dict(size=10.5, color=pal["text3"]), linecolor=pal["line"], ticks="")


def _value_axis(pal: dict, **kw) -> dict:
    return dict(rangemode="tozero", gridcolor=pal["grid"], zeroline=False, fixedrange=True, tickformat=",~r",
                tickfont=dict(size=10.5, color=pal["text3"]), ticks="", **kw)


def _rows(n: int, min_rows: int = 6) -> list[float]:
    """Reversed category range that keeps bar thickness sensible even with very few categories."""
    return [max(n, min_rows) - 0.5, -0.5]


def _collection_note(fig: go.Figure, x: list[int], pal: dict) -> None:
    """Mark the GTD collection change of 2012 on yearly charts (counts before and after are not strictly comparable)."""
    if x and x[0] < 2012 <= x[-1]:
        fig.add_vline(x=2011.5, line=dict(color=pal["line_strong"], width=1, dash="dot"))
        fig.add_annotation(x=2011.5, yref="paper", y=1, text="2012 collection change", showarrow=False, xanchor="right",
                           yanchor="top", xshift=-4, font=dict(size=10, color=pal["text3"]))


# --------------------------------------------------------------------------------------
# Incidents over time (overview area chart) and the incidents/fatalities combo (trends)
# --------------------------------------------------------------------------------------
def area_fig(yr: pd.DataFrame, pal: dict) -> go.Figure:
    x = yr.index.astype(int).tolist()
    fig = go.Figure(go.Scatter(
        x=x, y=yr["incidents"], mode="lines", line=dict(color=pal["red"], width=2.4, shape="spline", smoothing=0.5),
        fill="tozeroy", fillgradient=dict(type="vertical", colorscale=[[0, rgba(pal["red"], 0.0)], [1, rgba(pal["red"], 0.55)]]),
        hovertemplate="%{x}<br>Incidents  <b>%{y:,.0f}</b><extra></extra>"))
    _base(fig, pal, hovermode="x unified", margin=dict(l=2, r=6, t=8, b=2), showlegend=False,
          xaxis=_year_axis(x, pal), yaxis=_value_axis(pal))
    return fig


def _nice_step(vmax: float, n: int = 4) -> float:
    """Round tick step so that n intervals cover vmax (keeps two y axes on the same gridlines)."""
    if vmax is None or not np.isfinite(vmax) or vmax <= 0:
        return 1.0
    raw = vmax / n
    mag = 10 ** np.floor(np.log10(raw))
    return float(next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw))


def trend_combo_fig(yr: pd.DataFrame, pal: dict) -> go.Figure:
    x = yr.index.astype(int).tolist()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=x, y=yr["fatalities"], name="Reported fatalities", marker=dict(color=rgba(pal["red"], 0.75), line=dict(width=0)),
                         hovertemplate="Reported fatalities  <b>%{y:,.0f}</b><extra></extra>"), secondary_y=True)
    fig.add_trace(go.Scatter(x=x, y=yr["incidents"], name="Incidents", mode="lines+markers",
                             line=dict(color=pal["indigo"], width=2.6), marker=dict(size=6, color=pal["indigo"]),
                             hovertemplate="Incidents  <b>%{y:,.0f}</b><extra></extra>"), secondary_y=False)
    _collection_note(fig, x, pal)
    _base(fig, pal, hovermode="x unified", bargap=0.45, margin=dict(l=2, r=2, t=24, b=2), legend=_legend(pal), xaxis=_year_axis(x, pal))
    s1 = _nice_step(float(np.nanmax(np.r_[yr["incidents"].to_numpy(dtype=float), 0.0])))
    s2 = _nice_step(float(np.nanmax(np.r_[yr["fatalities"].to_numpy(dtype=float), 0.0])))
    fig.update_yaxes(_value_axis(pal), secondary_y=False, range=[0, 4.15 * s1], dtick=s1, tickfont=dict(size=10.5, color=pal["indigo"]))
    fig.update_yaxes(_value_axis(pal), secondary_y=True, range=[0, 4.15 * s2], dtick=s2, showgrid=False,
                     tickfont=dict(size=10.5, color=pal["red"]))
    return fig


def lines_fig(t: pd.DataFrame, pal: dict, colors: list[str], suffix: str = "", label_len: int = 24,
              note_2012: bool = False, y_range: list[float] | None = None) -> go.Figure:
    """One line per column over the year index (missing years stay gaps)."""
    x = t.index.astype(int).tolist()
    fig = go.Figure()
    for col, color in zip(t.columns, colors, strict=False):
        fig.add_trace(go.Scatter(x=x, y=t[col], name=short(str(col), label_len), mode="lines+markers", line=dict(color=color, width=2.2),
                                 marker=dict(size=4.5, color=color), customdata=[str(col)] * len(x),
                                 hovertemplate=f"{short(str(col), 40)}  <b>%{{y:,.1f}}{suffix}</b><extra></extra>"
                                 if suffix else f"{short(str(col), 40)}  <b>%{{y:,.0f}}</b><extra></extra>"))
    if note_2012:
        _collection_note(fig, x, pal)
    yaxis = _value_axis(pal, ticksuffix=suffix)
    if y_range:
        yaxis.update(range=y_range, rangemode="normal")
    _base(fig, pal, hovermode="x unified", margin=dict(l=2, r=2, t=24, b=2), legend=_legend(pal), xaxis=_year_axis(x, pal), yaxis=yaxis)
    return fig


def stack_share_fig(t: pd.DataFrame, pal: dict) -> go.Figure:
    """100% stacked area of shares per year (attack mix)."""
    x = t.index.astype(int).tolist()
    fig = go.Figure()
    for col, color in zip(t.columns, series_colors(pal, len(t.columns)), strict=True):
        fig.add_trace(go.Scatter(x=x, y=t[col].fillna(0), name=short(str(col), 18), mode="lines", stackgroup="one",
                                 line=dict(width=0.6, color=color), fillcolor=rgba(color, 0.78),
                                 customdata=[str(col)] * len(x),
                                 hovertemplate=f"{short(str(col), 30)}  <b>%{{y:.1f}}%</b><extra></extra>"))
    _base(fig, pal, hovermode="x unified", margin=dict(l=2, r=2, t=24, b=2), legend=_legend(pal, traceorder="normal"),
          xaxis=_year_axis(x, pal), yaxis=_value_axis(pal, ticksuffix="%", range=[0, 100]))
    return fig


def month_fig(mt: pd.DataFrame, pal: dict) -> go.Figure:
    peak = mt["incidents"].idxmax() if mt["incidents"].sum() else -1
    colors = [pal["red"] if i == peak else rgba(pal["red"], 0.45) for i in range(len(mt))]
    fig = go.Figure(go.Bar(x=mt["month"], y=mt["incidents"], marker=dict(color=colors, line=dict(width=0)), customdata=mt["share"],
                           hovertemplate="%{x}<br>Incidents  <b>%{y:,.0f}</b> (%{customdata:.1f}%)<extra></extra>"))
    _base(fig, pal, bargap=0.35, margin=dict(l=2, r=2, t=8, b=2), showlegend=False,
          xaxis=dict(type="category", showgrid=False, fixedrange=True, ticks="", tickfont=dict(size=10.5, color=pal["text3"])),
          yaxis=_value_axis(pal))
    return fig


# --------------------------------------------------------------------------------------
# Country choropleth (own Natural Earth projection: no tile server, no external request)
# --------------------------------------------------------------------------------------
def _project(lon, lat):
    lam, phi = np.radians(lon), np.radians(lat)
    p2 = phi * phi
    p4 = p2 * p2
    x = lam * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)))
    y = phi * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4)))
    return x, y


@functools.lru_cache(maxsize=1)
def _countries() -> tuple[list[dict], tuple[float, float], tuple[float, float]]:
    """Projected country rings as float32 arrays (NaN between rings), with the map's x and y ranges."""
    data = json.loads((ASSETS / "world_110m_countries.json").read_text(encoding="utf-8"))["countries"]
    out = []
    for c in data:
        xs, ys = [], []
        for ring in c["rings"]:
            a = np.asarray(ring, dtype=float)
            # rings that wrap around the antimeridian (Fiji, Russia) are cut there instead of being joined across the map
            for part in np.split(a, np.flatnonzero(np.abs(np.diff(a[:, 0])) > 180) + 1):
                x, y = _project(part[:, 0], part[:, 1])
                xs += [x, [np.nan]]
                ys += [y, [np.nan]]
        out.append({"name": c["name"], "gtd": c["gtd"], "x": np.concatenate(xs).astype(np.float32),
                    "y": np.concatenate(ys).astype(np.float32)})
    x0, _ = _project(np.array([-180.0]), np.array([0.0]))
    _, ylo = _project(np.array([0.0]), np.array([-57.0]))
    _, yhi = _project(np.array([0.0]), np.array([80.0]))
    return out, (float(x0[0]) * 1.005, -float(x0[0]) * 1.005), (float(ylo[0]), float(yhi[0]))


def map_bins(vmax: float) -> list[tuple[float, float, str]]:
    """Five classes scaled to the largest value: with a maximum of 24,475 they are >=10,000, 5,000-9,999,
    1,000-4,999, 100-999 and <100 (the mockup's legend); smaller selections shift down by powers of ten."""
    s = 10 ** int(np.floor(np.log10(max(vmax, 1))))
    edges = sorted({max(int(e), 1) for e in (s, s / 2, s / 10, s / 100)}, reverse=True)
    bins, hi = [], np.inf
    for e in edges:
        label = f"≥ {e:,}" if hi == np.inf else f"{e:,} – {int(hi) - 1:,}"
        bins.append((e, hi, label))
        hi = e
    if hi > 1:
        bins.append((1, hi, f"< {int(hi):,}"))
    return bins   # highest class first


METRIC_TEXT = {"incidents": "incidents", "fatalities": "reported fatalities", "injuries": "reported injuries"}


def map_classes(ct: pd.DataFrame, pal: dict, metric: str = "incidents") -> list[tuple[float, float, str, str]]:
    """(low, high, label, colour) per class, highest first; the colours run from darkest to lightest."""
    values = ct[metric].astype(float)
    vmax = float(values.max()) if len(values) and values.notna().any() else 0.0
    bins = map_bins(vmax)
    colors = list(reversed(pal["map_bins"]))[: len(bins)]
    return [(lo, hi, label, color) for (lo, hi, label), color in zip(bins, colors, strict=True)]


def choropleth_fig(ct: pd.DataFrame, pal: dict, metric: str = "incidents") -> go.Figure:
    """Countries shaded by class of ``metric``; the legend is HTML beside the map (theme.map_legend_html)."""
    countries, xr, yr = _countries()
    values = ct[metric].astype(float)
    classes = map_classes(ct, pal, metric)
    bins = [(lo, hi, label) for lo, hi, label, _ in classes]
    colors = [c for *_, c in classes]

    def klass(v: float) -> int | None:
        if pd.isna(v) or v <= 0:
            return None
        return next(i for i, (lo, _, _) in enumerate(bins) if v >= lo)

    def hover(name: str) -> str:
        r = ct.loc[name]
        return (f"<b>{name}</b><br>Incidents  {r['incidents']:,.0f}<br>Reported fatalities  {_num(r['fatalities'])}"
                f"<br>Reported injuries  {_num(r['injuries'])}")

    fig = go.Figure()
    blank_x, blank_y = [], []
    drawn = set()
    for c in countries:
        k = klass(values.get(c["gtd"], np.nan))
        if k is None:
            blank_x += [c["x"]]
            blank_y += [c["y"]]
            continue
        drawn.add(c["gtd"])
        fig.add_trace(go.Scatter(x=c["x"], y=c["y"], mode="lines", fill="toself", fillcolor=colors[k], hoveron="fills",
                                 line=dict(color=pal["map_line"], width=0.5), name=c["gtd"], text=hover(c["gtd"]),
                                 customdata=[c["gtd"]] * len(c["x"]),
                                 hoverinfo="text", showlegend=False))
    if blank_x:
        fig.add_trace(go.Scatter(x=np.concatenate(blank_x), y=np.concatenate(blank_y), mode="lines", fill="toself",
                                 fillcolor=pal["map_none"], line=dict(color=pal["map_line"], width=0.5), hoverinfo="skip",
                                 showlegend=False))
    # countries with incidents but no polygon at this scale (small islands, former states): a dot at their incidents' centre
    extra = ct[(~ct.index.isin(drawn)) & ct["lat"].notna() & (values > 0)]
    if len(extra):
        x, y = _project(extra["lon"].to_numpy(dtype=float), extra["lat"].to_numpy(dtype=float))
        fig.add_trace(go.Scatter(x=x, y=y, mode="markers", showlegend=False, hoverinfo="text",
                                 customdata=list(extra.index),
                                 text=[hover(n) for n in extra.index],
                                 marker=dict(size=7, color=[colors[klass(v)] for v in values[extra.index]],
                                             line=dict(color=pal["map_line"], width=1))))
    _base(fig, pal, dragmode="pan", uirevision="map", hovermode="closest", margin=dict(l=0, r=0, t=0, b=0),
          xaxis=dict(visible=False, range=list(xr), constrain="domain", fixedrange=False),
          yaxis=dict(visible=False, range=list(yr), scaleanchor="x", scaleratio=1, constrain="domain", fixedrange=False))
    return fig


# --------------------------------------------------------------------------------------
# Bars
# --------------------------------------------------------------------------------------
def hbar_fig(t: pd.DataFrame, pal: dict, value: str = "incidents", color: str | None = None, label_len: int = 22,
             value_name: str = "Incidents") -> go.Figure:
    color = color or pal["red"]
    full = list(t.index)
    vals = t[value].astype(float).tolist()
    custom = np.c_[full, [f"{s:.1f}%" for s in t["share"]], [_num(v) for v in t["fatalities"]], [_num(v) for v in t["injuries"]]]
    fig = go.Figure(go.Bar(
        y=[short(s, label_len) for s in full], x=vals, orientation="h", customdata=custom,
        marker=dict(color=color, line=dict(width=0), cornerradius=4),
        text=[f"{v:,.0f}" for v in vals], textposition="outside", cliponaxis=False,
        textfont=dict(size=11, color=pal["text"]),
        hovertemplate=(f"<b>%{{customdata[0]}}</b><br>{value_name}  <b>%{{x:,.0f}}</b> (%{{customdata[1]}})"
                       "<br>Reported fatalities  %{customdata[2]}<br>Reported injuries  %{customdata[3]}<extra></extra>")))
    _base(fig, pal, bargap=0.42, margin=dict(l=2, r=40, t=2, b=2),
          yaxis=dict(range=_rows(len(full)), showgrid=False, ticks="", automargin=True, fixedrange=True,
                     tickfont=dict(size=11.5, color=pal["text"])),
          xaxis=dict(visible=False, range=[0, max(vals + [1]) * 1.04], fixedrange=True))
    return fig


def dual_hbar_fig(t: pd.DataFrame, pal: dict, label_len: int = 24) -> go.Figure:
    """Incidents (left) and reported fatalities (right) per category, same row order."""
    full = list(t.index)
    labels = [short(s, label_len) for s in full]
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.07)
    for col, (field, name, color) in enumerate((("incidents", "Incidents", pal["indigo"]), ("fatalities", "Fatalities", pal["red"])), 1):
        v = t[field]
        fig.add_trace(go.Bar(y=labels, x=v, orientation="h", marker=dict(color=color, line=dict(width=0), cornerradius=3),
                             text=[("" if pd.isna(x) else f"{x:,.0f}") for x in v], textposition="outside", cliponaxis=False,
                             textfont=dict(size=10.5, color=pal["text2"]), customdata=full,
                             hovertemplate=f"<b>%{{customdata}}</b><br>{name}  <b>%{{x:,.0f}}</b><extra></extra>"), row=1, col=col)
        fig.update_xaxes(range=[0, float(np.nanmax(np.r_[v.to_numpy(dtype=float), 1.0])) * 1.42], row=1, col=col)
    _base(fig, pal, bargap=0.38, showlegend=False, margin=dict(l=2, r=6, t=20, b=2))
    fig.update_yaxes(range=_rows(len(full)), showgrid=False, ticks="", automargin=True, fixedrange=True,
                     tickfont=dict(size=11.5, color=pal["text"]))
    fig.update_xaxes(visible=False, fixedrange=True)
    for ref, text, color in (("x domain", "Incidents", pal["indigo"]), ("x2 domain", "Fatalities", pal["red"])):
        fig.add_annotation(xref=ref, yref="paper", x=0, y=1.0, xanchor="left", yanchor="bottom", showarrow=False,
                           text=text, font=dict(size=11, color=color))
    return fig


def lethality_scatter_fig(t: pd.DataFrame, pal: dict, min_known: int = 15) -> go.Figure:
    """Reported fatalities vs. incidents with a known count; guide lines mark 1 and 10 per incident."""
    d = t[(t["fatal_known"] >= min_known) & t["fatalities"].notna() & (t["fatalities"] > 0)]
    fig = go.Figure()
    if len(d) >= 2:
        lo, hi = float(d["fatal_known"].min()) * 0.7, float(d["fatal_known"].max()) * 1.6
        for ratio in (1, 10):
            fig.add_trace(go.Scatter(x=[lo, hi], y=[lo * ratio, hi * ratio], mode="lines", hoverinfo="skip", showlegend=False,
                                     line=dict(color=pal["line_strong"], width=1, dash="dot")))
        fig.add_trace(go.Scatter(
            x=d["fatal_known"], y=d["fatalities"], mode="markers", showlegend=False, customdata=np.c_[d.index, d["incidents"]],
            marker=dict(size=9, color=rgba(pal["red"], 0.55), line=dict(color=pal["red"], width=0.8)),
            hovertemplate=("<b>%{customdata[0]}</b><br>Incidents with a known count  %{x:,.0f}<br>Reported fatalities  %{y:,.0f}"
                           "<extra></extra>")))
        lx, ly = np.log10(d["fatal_known"].astype(float)), np.log10(d["fatalities"].astype(float))
        span_x, span_y = max(lx.max() - lx.min(), 1e-9), max(ly.max() - ly.min(), 1e-9)
        boxes: list[tuple[float, float, float, float]] = []
        for name in d["fatalities"].sort_values(ascending=False).index:
            px, py = (lx[name] - lx.min()) / span_x * 300, (ly[name] - ly.min()) / span_y * 190   # rough pixel space
            text = short(str(name), 14)
            box = (px - 8 - len(text) * 6, py - 8, px - 8, py + 8)
            if any(not (box[2] < b[0] or box[0] > b[2] or box[3] < b[1] or box[1] > b[3]) for b in boxes):
                continue
            boxes.append(box)
            fig.add_annotation(x=lx[name], y=ly[name], xref="x", yref="y", text=text, showarrow=False, xanchor="right", xshift=-8,
                               font=dict(size=10, color=pal["text"]))
            if len(boxes) >= 5:
                break
    axis = dict(type="log", gridcolor=pal["grid"], zeroline=False, fixedrange=True, tickfont=dict(size=10.5, color=pal["text3"]), ticks="")
    _base(fig, pal, margin=dict(l=2, r=6, t=4, b=2),
          xaxis=dict(**axis, title=dict(text="Incidents with a known fatality count (15 or more)", font=dict(size=10.5, color=pal["text3"]))),
          yaxis=dict(**axis, title=dict(text="Reported fatalities", font=dict(size=10.5, color=pal["text3"]))))
    return fig


def heatmap_fig(m: pd.DataFrame, pal: dict, col_len: int = 12) -> go.Figure:
    z = m.to_numpy(dtype=float)
    text = [[f"{v / 1000:.1f}k" if v >= 1000 else (f"{int(v)}" if v else "") for v in row] for row in z]
    heat = pal["heat"]
    customdata = [[[str(i), str(c), float(val)] for c, val in zip(m.columns, row, strict=True)] for i, row in zip(m.index, z, strict=True)]
    fig = go.Figure(go.Heatmap(
        z=np.sqrt(z), x=[short(c, col_len) for c in m.columns], y=[short(i, 18) for i in m.index], text=text, texttemplate="%{text}",
        textfont=dict(size=10, color=pal["text"]), customdata=customdata, xgap=2, ygap=2, showscale=False,
        colorscale=[[0, heat[0]], [0.3, heat[1]], [0.65, heat[2]], [1, heat[3]]],
        hovertemplate="<b>%{y}</b> on <b>%{x}</b><br>%{customdata[2]:,.0f} incidents<extra></extra>"))
    _base(fig, pal, margin=dict(l=2, r=2, t=2, b=2),
          xaxis=dict(side="top", showgrid=False, ticks="", fixedrange=True, tickfont=dict(size=10.5, color=pal["text2"]), tickangle=-30),
          yaxis=dict(range=_rows(len(m), 5), showgrid=False, ticks="", automargin=True, fixedrange=True,
                     tickfont=dict(size=11, color=pal["text"])))
    return fig


# --------------------------------------------------------------------------------------
# Human impact
# --------------------------------------------------------------------------------------
def casualties_year_fig(yr: pd.DataFrame, pal: dict) -> go.Figure:
    x = yr.index.astype(int).tolist()
    fig = go.Figure()
    for col, name, color in (("injuries", "Reported injuries", pal["red_soft"]), ("fatalities", "Reported fatalities", pal["red"])):
        fig.add_trace(go.Scatter(x=x, y=yr[col], name=name, mode="lines+markers", line=dict(color=color, width=2.4),
                                 marker=dict(size=5, color=color), hovertemplate=f"{name}  <b>%{{y:,.0f}}</b><extra></extra>"))
    _collection_note(fig, x, pal)
    _base(fig, pal, hovermode="x unified", margin=dict(l=2, r=2, t=24, b=2), legend=_legend(pal), xaxis=_year_axis(x, pal),
          yaxis=_value_axis(pal))
    return fig


def fatality_dist_fig(t: pd.DataFrame, pal: dict) -> go.Figure:
    labels = list(t.index)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=labels, y=t["pct_incidents"], name="Share of incidents", marker=dict(color=pal["indigo"], line=dict(width=0)),
                         customdata=np.c_[t["incidents"]],
                         hovertemplate="%{x} fatalities<br>Share of incidents  <b>%{y:.1f}%</b> (%{customdata[0]:,.0f})<extra></extra>"))
    fig.add_trace(go.Bar(x=labels, y=t["pct_fatalities"], name="Share of reported fatalities", marker=dict(color=pal["red"], line=dict(width=0)),
                         customdata=np.c_[t["fatalities"]],
                         hovertemplate="%{x} fatalities<br>Share of reported fatalities  <b>%{y:.1f}%</b> (%{customdata[0]:,.0f})<extra></extra>"))
    _base(fig, pal, barmode="group", bargap=0.28, bargroupgap=0.06, hovermode="x unified", margin=dict(l=2, r=2, t=24, b=2),
          legend=_legend(pal),
          xaxis=dict(type="category", showgrid=False, zeroline=False, fixedrange=True, ticks="", tickfont=dict(size=11, color=pal["text2"]),
                     title=dict(text="Reported fatalities in the incident", font=dict(size=10.5, color=pal["text3"]))),
          yaxis=_value_axis(pal, ticksuffix="%"))
    return fig


def casualties_attack_fig(t: pd.DataFrame, pal: dict, n: int = 7) -> go.Figure:
    d = t.head(n)
    labels = [short(s, 20) for s in d.index]
    fig = go.Figure()
    for field, name, color in (("fatalities", "Reported fatalities", pal["red"]), ("injuries", "Reported injuries", pal["red_soft"])):
        fig.add_trace(go.Bar(y=labels, x=d[field], orientation="h", name=name, customdata=list(d.index),
                             marker=dict(color=color, line=dict(width=0)),
                             hovertemplate=f"<b>%{{customdata}}</b><br>{name}  <b>%{{x:,.0f}}</b><extra></extra>"))
    _base(fig, pal, barmode="stack", bargap=0.42, margin=dict(l=2, r=2, t=24, b=2), legend=_legend(pal, traceorder="normal"),
          yaxis=dict(range=_rows(len(d)), showgrid=False, ticks="", automargin=True, fixedrange=True, tickfont=dict(size=11.5, color=pal["text"])),
          xaxis=_value_axis(pal))
    return fig


def missing_fig(t: pd.DataFrame, pal: dict) -> go.Figure:
    return lines_fig(t.rename(columns={"fatalities": "Fatality count missing", "injuries": "Injury count missing"}), pal,
                     [pal["red"], pal["red_soft"]], suffix="%", note_2012=True)


# --------------------------------------------------------------------------------------
# Small companions of the statistical tests
# --------------------------------------------------------------------------------------
def band_heatmap_fig(m: pd.DataFrame, pal: dict) -> go.Figure:
    """Fatality band (rows) by injury band (columns), incidents with both counts known."""
    z = m.to_numpy(dtype=float)
    text = [[f"{v / 1000:.1f}k" if v >= 1000 else (f"{int(v)}" if v else "") for v in row] for row in z]
    heat = pal["heat"]
    fig = go.Figure(go.Heatmap(
        z=np.sqrt(z), x=list(m.columns), y=list(m.index), text=text, texttemplate="%{text}", textfont=dict(size=9.5, color=pal["text"]),
        customdata=z, xgap=2, ygap=2, showscale=False, colorscale=[[0, heat[0]], [0.3, heat[1]], [0.65, heat[2]], [1, heat[3]]],
        hovertemplate="Fatalities <b>%{y}</b>, injuries <b>%{x}</b><br>%{customdata:,.0f} incidents<extra></extra>"))
    _base(fig, pal, margin=dict(l=2, r=2, t=2, b=2),
          xaxis=dict(type="category", side="bottom", showgrid=False, ticks="", fixedrange=True, tickfont=dict(size=10, color=pal["text2"]),
                     title=dict(text="Reported injuries", font=dict(size=10.5, color=pal["text3"]))),
          yaxis=dict(type="category", autorange="reversed", showgrid=False, ticks="", fixedrange=True, tickfont=dict(size=10, color=pal["text2"]),
                     title=dict(text="Reported fatalities", font=dict(size=10.5, color=pal["text3"]))))
    return fig


def suicide_bands_fig(t: pd.DataFrame, pal: dict) -> go.Figure:
    fig = go.Figure()
    for col, color in (("Suicide attacks", pal["red"]), ("Other attacks", pal["indigo"])):
        fig.add_trace(go.Bar(x=list(t.index), y=t[col], name=col, marker=dict(color=color, line=dict(width=0)),
                             hovertemplate=f"{col}<br>%{{x}} fatalities  <b>%{{y:.1f}}%</b> of incidents<extra></extra>"))
    _base(fig, pal, barmode="group", bargap=0.25, bargroupgap=0.05, hovermode="x unified", margin=dict(l=2, r=2, t=24, b=2),
          legend=_legend(pal, entrywidth=105, entrywidthmode="pixels"),
          xaxis=dict(type="category", showgrid=False, ticks="", fixedrange=True, tickfont=dict(size=10.5, color=pal["text2"]),
                     title=dict(text="Reported fatalities in the incident", font=dict(size=10.5, color=pal["text3"]))),
          yaxis=_value_axis(pal, ticksuffix="%"))
    return fig


def attack_means_fig(t: pd.DataFrame, pal: dict) -> go.Figure:
    labels = [short(i, 18) for i in t.index]
    fig = go.Figure()
    fig.add_trace(go.Bar(y=labels, x=t["mean"], orientation="h", name="Mean", customdata=np.c_[list(t.index), t["n"], t["median"]],
                         marker=dict(color=pal["red"], line=dict(width=0), cornerradius=3),
                         text=[f"{v:.1f}" for v in t["mean"]], textposition="outside", cliponaxis=False, textfont=dict(size=10.5, color=pal["text2"]),
                         hovertemplate="<b>%{customdata[0]}</b><br>Mean reported fatalities  <b>%{x:.1f}</b><br>Median  %{customdata[2]:.0f}"
                                       "<br>Incidents with a count  %{customdata[1]:,.0f}<extra></extra>"))
    fig.add_trace(go.Scatter(y=labels, x=t["median"], mode="markers", name="Median", hoverinfo="skip",
                             marker=dict(symbol="diamond", size=8, color=pal["text"], line=dict(color=pal["card"], width=1))))
    _base(fig, pal, bargap=0.4, margin=dict(l=2, r=26, t=24, b=2), legend=_legend(pal, entrywidth=70, entrywidthmode="pixels"),
          yaxis=dict(range=_rows(len(t)), showgrid=False, ticks="", automargin=True, fixedrange=True, tickfont=dict(size=11, color=pal["text"])),
          xaxis=dict(visible=False, range=[0, float(t["mean"].max()) * 1.18], fixedrange=True))
    return fig

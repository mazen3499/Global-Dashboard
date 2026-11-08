"""AEGIS design system: tokens (dark and light), CSS, icons and HTML builders.

Nothing in this module touches the data. Every colour lives in PALETTES; the CSS reads the active palette
through custom properties and the chart builders receive the same palette as a dict, so the two modes
can never drift apart.
"""
from __future__ import annotations

import base64
import functools
import html
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
FONTS = ROOT / "static" / "fonts"
STATIC_URL = "app/static"   # Streamlit static serving (see .streamlit/config.toml)

FONT_SANS = "'Instrument Sans','Segoe UI Variable','Segoe UI',system-ui,-apple-system,sans-serif"

# --------------------------------------------------------------------------------------
# tokens
# --------------------------------------------------------------------------------------
_SHARED = {
    "red": "#EF3B4F", "red_deep": "#C8162D", "red_soft": "#F7A3AC",
    "indigo": "#6D5EF6", "violet": "#8B5CF6",
    "green": "#22C55E", "orange": "#F97B3D", "yellow": "#F5B83D", "teal": "#22C3A6", "cyan": "#2BB0D6",
    "purple": "#9B6CF6",
}
PALETTES = {
    "dark": {
        **_SHARED,
        "bg": "#000000", "side": "#000000", "card": "#0A0A0C", "raised": "#141417", "line": "#1E1E23",
        "line_strong": "#2E2E35", "text": "#F5F5F7", "text2": "#A1A1AA", "text3": "#6B6B75",
        "nav_on": "rgba(109,94,246,.24)", "nav_on_text": "#FFFFFF", "accent_soft": "rgba(109,94,246,.16)",
        "red_tint": "rgba(239,59,79,.14)", "grid": "rgba(255,255,255,.07)", "hover_bg": "#141417",
        "map_none": "#232328", "map_line": "#0A0A0C", "track": "#1A1A1F",
        "map_bins": ["#F9D3D7", "#F4A0A9", "#EC6371", "#DD2F41", "#A90F22"],
        "heat": ["#141417", "#4A1820", "#9C2236", "#EF3B4F"],
        "shadow": "none", "globe": "globe-dark.svg", "page_glow": "rgba(0,0,0,0)",
    },
    "light": {
        **_SHARED,
        "red": "#E2283C", "red_deep": "#B8122A",
        "bg": "#F4F5FB", "side": "#FFFFFF", "card": "#FFFFFF", "raised": "#F6F7FC", "line": "#E6E8F2",
        "line_strong": "#D5D9E8", "text": "#121629", "text2": "#4D556E", "text3": "#8A91AB",
        "nav_on": "#ECE9FE", "nav_on_text": "#4338CA", "accent_soft": "#EEEBFF",
        "red_tint": "#FDEBED", "grid": "rgba(77,85,110,.10)", "hover_bg": "#FFFFFF",
        "map_none": "#E3E6F0", "map_line": "#FFFFFF", "track": "#EEF0F7",
        "map_bins": ["#FCE0E3", "#F7B3BA", "#EF7884", "#E03A4C", "#B30F24"],
        "heat": ["#F6F7FC", "#F8C9CF", "#EC6E7C", "#C8162D"],
        "shadow": "0 1px 2px rgba(18,22,41,.04), 0 6px 20px rgba(18,22,41,.05)", "globe": "globe-light.svg",
        "page_glow": "rgba(109,94,246,.06)",
    },
}
# Attack-type colours of the donut and every chart that shows attack types (same order everywhere).
SERIES = ["red", "orange", "yellow", "teal", "cyan", "purple"]


def palette(mode: str) -> dict:
    return PALETTES.get(mode, PALETTES["dark"])


def esc(x) -> str:
    return html.escape(str(x), quote=True)


# --------------------------------------------------------------------------------------
# number formatting
# --------------------------------------------------------------------------------------
def _missing(x) -> bool:
    return x is None or (isinstance(x, float) and np.isnan(x))


def fmt_int(x) -> str:
    return "n/a" if _missing(x) else f"{int(round(x)):,}"


def fmt_pct(x, d: int = 1) -> str:
    return "n/a" if _missing(x) else f"{x:.{d}f}%"


def fmt_share(frac, d: int = 1) -> str:
    """A 0-1 fraction as a percentage; n/a when there is nothing to divide (an empty selection)."""
    return "n/a" if _missing(frac) else f"{100 * frac:.{d}f}%"


def fmt_num(x, d: int = 1) -> str:
    return "n/a" if _missing(x) else f"{x:,.{d}f}"


def fmt_p(p) -> str:
    if _missing(p):
        return "n/a"
    return "< 0.001" if p < 0.001 else f"{p:.3f}"


def fmt_delta(x) -> str:
    return "n/a" if _missing(x) else f"{x:+.1f}%"


# --------------------------------------------------------------------------------------
# icons: Google Material Symbols (Rounded), the icon font Streamlit already bundles, so no download
# and no external request. Each name below is a Material Symbols ligature.
# --------------------------------------------------------------------------------------
ICONS = {
    "overview": "space_dashboard", "incidents": "crisis_alert", "groups": "groups", "regions": "public",
    "trends": "trending_up", "impact": "ecg_heart", "analysis": "query_stats", "data": "database",
    "target": "target", "people": "groups", "casualties": "personal_injury", "fatalities": "deceased",
    "trend_up": "trending_up", "trend_down": "trending_down", "calendar": "calendar_month", "info": "info",
    "flag": "flag", "attack": "explosion", "building": "apartment", "search": "search",
    "timeline": "timeline", "travel_explore": "travel_explore", "city": "location_city", "bomb": "bomb",
    "crosshair": "my_location", "unknown": "question_mark", "claim": "campaign", "warning": "warning",
    "verified": "verified", "bulb": "lightbulb",
}
TOPIC_ICON = {"Trend": "trends", "Geography": "regions", "Method": "attack", "Groups": "groups",
              "Human impact": "impact", "Data quality": "data"}
NAV = [("Overview", "overview"), ("Incidents", "incidents"), ("Groups", "groups"), ("Regions", "regions"),
       ("Trends", "trends"), ("Human Impact", "impact"), ("Analysis", "analysis"), ("Data & Methods", "data")]
SYMBOLS = "'Material Symbols Rounded'"


def icon(name: str, size: int = 18, filled: bool = False) -> str:
    """A Material Symbols icon; it takes the surrounding text colour, so it follows the theme."""
    fill = " fill" if filled else ""
    return f'<span class="ms{fill}" style="font-size:{size}px" aria-hidden="true">{ICONS[name]}</span>'


def _img(svg: str, w: int, h: int, cls: str = "", alt: str = "") -> str:
    src = "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()
    return f'<img class="{cls}" src="{src}" width="{w}" height="{h}" alt="{esc(alt)}"/>'


def _shield() -> str:
    return _img('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 52"><defs>'
                '<linearGradient id="sg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#8B7CFF"/>'
                '<stop offset="1" stop-color="#4F3FD8"/></linearGradient></defs>'
                '<path d="M24 2 44 9v15c0 12.5-8.6 22.6-20 26C12.6 46.6 4 36.5 4 24V9z" fill="url(#sg)"/>'
                '<path d="M24 7.5 39 13v11c0 9.6-6.3 17.6-15 20.6C15.3 41.6 9 33.6 9 24V13z" fill="#0B1024" opacity=".35"/>'
                '<circle cx="24" cy="24.5" r="9" fill="none" stroke="#fff" stroke-width="1.8"/>'
                '<path d="M15 24.5h18M24 15.5c2.6 2.6 3.8 5.5 3.8 9s-1.2 6.4-3.8 9c-2.6-2.6-3.8-5.5-3.8-9s1.2-6.4 3.8-9z"'
                ' fill="none" stroke="#fff" stroke-width="1.6"/><circle cx="33" cy="15" r="3.2" fill="#EF3B4F"/></svg>',
                40, 44, "logo", "AEGIS")


# --------------------------------------------------------------------------------------
# 3D self-folding animated globe (inline base64 so it works everywhere without static serving)
# --------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=4)
def _globe_data_uris(mode: str) -> tuple[str, str]:
    p = palette(mode)
    stroke_main = "#6D5EF6" if mode == "dark" else "#4F46E5"
    stroke_sub = "#8B5CF6" if mode == "dark" else "#6366F1"
    stroke_red = "#EF3B4F"
    glow_op = "0.28" if mode == "dark" else "0.14"

    # 1. Base globe: read bundled static SVG if available, otherwise build a rich wireframe base
    svg_path = ROOT / "static" / p["globe"]
    if not svg_path.exists():
        svg_path = ASSETS / p["globe"]
    if svg_path.exists():
        raw_base = svg_path.read_bytes()
    else:
        fallback_svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">'
            f'<circle cx="160" cy="160" r="132" fill="none" stroke="{stroke_main}" stroke-width="1.2" opacity="0.45"/>'
            f'<circle cx="160" cy="160" r="98" fill="none" stroke="{stroke_sub}" stroke-width="1" stroke-dasharray="4 6" opacity="0.4"/>'
            f'</svg>'
        )
        raw_base = fallback_svg.encode("utf-8")

    # 2. Inner 3D self-folding core: meridian rings continuously morph rx (126 -> 4 -> 126)
    #    and counter-rotate so the globe folds into itself in 3D space.
    core_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 320">
    <defs>
      <radialGradient id="gGlow" cx="50%" cy="50%" r="50%">
        <stop offset="0%" stop-color="{stroke_main}" stop-opacity="{glow_op}"/>
        <stop offset="65%" stop-color="{stroke_sub}" stop-opacity="0.08"/>
        <stop offset="100%" stop-color="{stroke_main}" stop-opacity="0"/>
      </radialGradient>
    </defs>
    <circle cx="160" cy="160" r="145" fill="url(#gGlow)"/>
    <g transform="rotate(-22 160 160)">
      <circle cx="160" cy="160" r="134" fill="none" stroke="{stroke_main}" stroke-width="1.3" stroke-dasharray="8 6" opacity="0.55">
        <animateTransform attributeName="transform" type="rotate" from="0 160 160" to="360 160 160" dur="24s" repeatCount="indefinite"/>
      </circle>
      <circle cx="160" cy="160" r="126" fill="none" stroke="{stroke_sub}" stroke-width="1.1" opacity="0.45"/>
      <!-- Latitude rings -->
      <ellipse cx="160" cy="160" rx="126" ry="42" fill="none" stroke="{stroke_main}" stroke-width="1" stroke-dasharray="5 5" opacity="0.45"/>
      <ellipse cx="160" cy="122" rx="108" ry="28" fill="none" stroke="{stroke_sub}" stroke-width="0.9" opacity="0.35"/>
      <ellipse cx="160" cy="198" rx="108" ry="28" fill="none" stroke="{stroke_sub}" stroke-width="0.9" opacity="0.35"/>
      <!-- Self-folding 3D meridians (staggered rx morphing) -->
      <ellipse cx="160" cy="160" rx="126" ry="126" fill="none" stroke="{stroke_main}" stroke-width="1.3" opacity="0.65">
        <animate attributeName="rx" values="126;4;126" dur="8s" begin="0s" repeatCount="indefinite"/>
      </ellipse>
      <ellipse cx="160" cy="160" rx="90" ry="126" fill="none" stroke="{stroke_sub}" stroke-width="1.2" opacity="0.55">
        <animate attributeName="rx" values="126;4;126" dur="8s" begin="-2s" repeatCount="indefinite"/>
      </ellipse>
      <ellipse cx="160" cy="160" rx="45" ry="126" fill="none" stroke="{stroke_main}" stroke-width="1.2" opacity="0.55">
        <animate attributeName="rx" values="126;4;126" dur="8s" begin="-4s" repeatCount="indefinite"/>
      </ellipse>
      <ellipse cx="160" cy="160" rx="15" ry="126" fill="none" stroke="{stroke_sub}" stroke-width="1.2" opacity="0.55">
        <animate attributeName="rx" values="126;4;126" dur="8s" begin="-6s" repeatCount="indefinite"/>
      </ellipse>
      <!-- Inner gyroscopic ring folding into the core -->
      <ellipse cx="160" cy="160" rx="96" ry="96" fill="none" stroke="{stroke_red}" stroke-width="1.1" stroke-dasharray="3 7" opacity="0.55">
        <animate attributeName="ry" values="96;12;96" dur="6s" repeatCount="indefinite"/>
        <animateTransform attributeName="transform" type="rotate" from="360 160 160" to="0 160 160" dur="14s" repeatCount="indefinite"/>
      </ellipse>
      <!-- Tactical pulse nodes -->
      <circle cx="215" cy="118" r="3.2" fill="{stroke_red}">
        <animate attributeName="r" values="2.2;4.5;2.2" dur="2.4s" repeatCount="indefinite"/>
        <animate attributeName="opacity" values="0.95;0.35;0.95" dur="2.4s" repeatCount="indefinite"/>
      </circle>
      <circle cx="125" cy="96" r="2.8" fill="{stroke_main}">
        <animate attributeName="r" values="2;4;2" dur="3.1s" repeatCount="indefinite"/>
      </circle>
      <circle cx="238" cy="172" r="2.6" fill="{stroke_red}">
        <animate attributeName="opacity" values="0.3;1;0.3" dur="1.9s" repeatCount="indefinite"/>
      </circle>
    </g>
    </svg>"""

    uri_base = "url(\"data:image/svg+xml;base64," + base64.b64encode(raw_base).decode() + "\")"
    uri_core = "url(\"data:image/svg+xml;base64," + base64.b64encode(core_svg.encode("utf-8")).decode() + "\")"
    return uri_base, uri_core


# --------------------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------------------
@functools.lru_cache(maxsize=1)
def font_face_css() -> str:
    """@font-face rules pointing at the statically served fonts (a few hundred bytes, not the font data)."""
    spec = [("Instrument Sans", 400, "instrument-sans-latin-400-normal.woff2"),
            ("Instrument Sans", 500, "instrument-sans-latin-500-normal.woff2"),
            ("Instrument Sans", 600, "instrument-sans-latin-600-normal.woff2")]
    out = []
    for family, weight, fname in spec:
        if not (FONTS / fname).exists():  # falls back to the system font stack
            continue
        out.append(f"@font-face{{font-family:'{family}';font-weight:{weight};font-style:normal;font-display:swap;"
                   f"src:url({STATIC_URL}/fonts/{fname}) format('woff2');}}")
    return "".join(out)


def _root_vars(mode: str) -> str:
    p = palette(mode)
    globe_base, globe_core = _globe_data_uris(mode)
    v = {f"--{k.replace('_', '-')}": val for k, val in p.items() if isinstance(val, str) and k not in ("globe",)}
    v.update({"--sans": FONT_SANS, "--globe": globe_base, "--globe-core": globe_core,
              "--side-w": "220px", "--pad-t": "14px", "--pad-b": "8px", "--head": "52px", "--kpi": "72px",
              "--gap": "12px", "--foot": "16px", "--radius": "12px"})
    scheme = "dark" if mode == "dark" else "light"
    return ":root{color-scheme:" + scheme + ";" + ";".join(f"{k}:{val}" for k, val in v.items()) + "}"


def _nav_icon_css() -> str:
    return "".join(f'div.st-key-nav [data-testid="stRadioGroup"] > div:nth-child({i}) label::before{{content:"{ICONS[ic]}"}}'
                   for i, (_, ic) in enumerate(NAV, start=1))


def _filter_icon_css() -> str:
    pairs = [("f_regions", "regions"), ("f_countries", "flag"), ("f_groups", "groups"), ("f_attacks", "attack"),
             ("f_targets", "building"), ("q", "search")]
    return "".join(f'div.st-key-{k} :is([data-testid="stMultiSelect"] div[role="group"], [data-testid="stTextInputRootElement"])::before'
                   f'{{content:"{ICONS[ic]}"}}' for k, ic in pairs)


BASE_CSS = r"""
/* ---------- Streamlit chrome a dashboard does not need ---------- */
[data-testid="stDecoration"], footer, #MainMenu, [data-testid="stStatusWidget"], [data-testid="stToolbarActions"],
[data-testid="stAppDeployButton"] {display:none !important}
@media (min-width: 1180px){
  header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stSidebarHeader"], [data-testid="stSidebarCollapseButton"],
  [data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] {display:none !important}
}
[data-testid="stElementContainer"]:has(> style), [data-testid="stElementContainer"]:has(> [data-testid="stHtml"] > style),
[data-testid="stElementContainer"]:has(iframe[srcdoc*="__aegisSearchKey"]){display:none !important}
[data-stale="true"], [data-stale="true"] * {opacity:1 !important; transition:none !important}

/* ---------- base ---------- */
html, body, .stApp, [data-testid="stAppViewContainer"]{background:var(--bg) !important;color:var(--text);font-family:var(--sans)}
.stApp{background:radial-gradient(1100px 520px at 70% -10%, var(--page-glow), transparent 60%), var(--bg) !important}
.stApp, .stApp button, .stApp input, .stApp textarea, .stApp label, .stApp p, .stApp div, .stApp span, .stApp li{font-family:var(--sans)}
span[data-testid="stIconMaterial"], span[data-testid="stIconMaterial"] *{font-family:"Material Symbols Rounded","Material Symbols Outlined" !important;letter-spacing:0 !important}
.stApp p, .stApp label, .stApp span{color:inherit}
::selection{background:rgba(109,94,246,.30)}
*{scrollbar-width:thin;scrollbar-color:var(--line-strong) transparent}
.stApp .ms, .ms{font-family:'Material Symbols Rounded' !important;font-weight:normal;font-style:normal;line-height:1;letter-spacing:0 !important;
  text-transform:none;display:inline-block;white-space:nowrap;direction:ltr;font-feature-settings:'liga';-webkit-font-smoothing:antialiased;
  font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;width:1em;height:1em;overflow:hidden;flex:none;vertical-align:middle}
.stApp .ms.fill, .ms.fill{font-variation-settings:'FILL' 1,'wght' 400,'GRAD' 0,'opsz' 24}

/* ---------- main canvas ---------- */
[data-testid="stMain"]{overflow-x:hidden}
[data-testid="stMainBlockContainer"]{padding:var(--pad-t) 22px var(--pad-b) 22px !important;max-width:none !important}
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"]{gap:var(--gap) !important}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"]{min-width:0}
[data-testid="stElementContainer"]{margin:0 !important}

/* ---------- desktop: header, KPI band and two rows of panels fill exactly one screen ---------- */
@media (min-width: 1180px){
  div.st-key-hdr{height:var(--head) !important;flex:0 0 auto !important;justify-content:center}
  div.st-key-body{height:var(--body) !important;flex:0 0 auto !important}
  :is(div.st-key-body, div[class*="st-key-row_"], div[class*="st-key-p_s_"]) > [data-testid="stLayoutWrapper"]{height:100% !important;flex:1 1 0 !important;min-height:0 !important}
  :is(div.st-key-body, div[class*="st-key-row_"], div[class*="st-key-p_s_"]) > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"]{height:100% !important;align-items:stretch !important;flex-wrap:nowrap !important;gap:var(--gap) !important}
  :is(div.st-key-body, div[class*="st-key-row_"], div[class*="st-key-p_s_"]) > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{height:100% !important;min-width:0 !important}
  :is(div.st-key-body, div[class*="st-key-row_"], div[class*="st-key-p_s_"]) > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"]{height:100% !important;gap:var(--gap) !important}
  :is(div.st-key-body, div[class*="st-key-row_"]) > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]{flex:1 1 0 !important;min-height:0 !important}
  [data-testid="stLayoutWrapper"]:has(> div.st-key-row_a){flex-grow:var(--fa) !important}
  [data-testid="stLayoutWrapper"]:has(> div.st-key-row_b){flex-grow:calc(1 - var(--fa)) !important}
  div[class*="st-key-row_"]{height:100% !important}
  div[class*="st-key-p_"]{height:100% !important;min-height:0 !important}
  div[class*="st-key-p_"] > [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){flex:1 1 0 !important;height:auto !important;min-height:0}
  div[class*="st-key-p_s_"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){flex:1 1 0 !important;height:auto !important;min-height:0 !important}
  div[class*="st-key-p_"] > [data-testid="stElementContainer"]:has(.fill){flex:1 1 0 !important;min-height:0;overflow:hidden}
  div[class*="st-key-p_"] > [data-testid="stElementContainer"]:has(.fill) [data-testid="stHtml"]{height:100%}
}

/* ---------- page header ---------- */
div.st-key-hdr [data-testid="stHorizontalBlock"]{align-items:center !important;flex-wrap:nowrap !important;gap:10px !important}
.ttl{font-size:26px;font-weight:600;letter-spacing:-.01em;line-height:1.1;color:var(--text);white-space:nowrap}
.sub{font-size:13px;color:var(--text2);margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
div.st-key-q [data-testid="stTextInputRootElement"], div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]{position:relative}
div.st-key-q [data-testid="stTextInputRootElement"]::before, div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]::before{position:absolute;left:10px;top:50%;
  transform:translateY(-50%);color:var(--text3);font-family:'Material Symbols Rounded';font-size:18px;line-height:1;width:18px;height:18px;overflow:hidden;
  font-feature-settings:'liga';font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 20;z-index:2;pointer-events:none}
div.st-key-q input{padding-left:36px !important}
div.st-key-q [data-testid="stTextInputRootElement"]{height:40px;border-radius:10px !important;background:var(--card) !important;border:1px solid var(--line) !important;box-shadow:var(--shadow)}
div.st-key-q [data-testid="stTextInputRootElement"]:focus-within{border-color:var(--indigo) !important}
div.st-key-q [data-testid="stTextInputRootElement"] > div{background:transparent !important;border:0 !important}
.kbd{position:absolute;right:12px;top:50%;transform:translateY(-50%);font-size:11px;color:var(--text3);border:1px solid var(--line-strong);border-radius:5px;padding:1px 6px;pointer-events:none}
div.st-key-hdr [data-testid="stPopoverButton"]{height:40px;min-height:40px;border-radius:10px !important;background:transparent !important;border:1px solid transparent !important;color:var(--text2) !important;padding:0 10px !important}
div.st-key-hdr [data-testid="stPopoverButton"]:hover{background:var(--card) !important;border-color:var(--line) !important;color:var(--text) !important}
div.st-key-pop_date [data-testid="stPopoverButton"]{border:1px solid var(--indigo) !important;color:var(--text) !important;background:var(--card) !important;padding:0 14px !important;box-shadow:var(--shadow)}
div:is(.st-key-pop_bell, .st-key-pop_gear) [data-testid="stPopoverButton"] div[aria-hidden="true"]{display:none}
div.st-key-hdr [data-testid="stPopoverButton"] p{font-size:14px !important;font-weight:500;white-space:nowrap}
div.st-key-hdr [data-testid="stPopoverButton"] span[data-testid="stIconMaterial"]{font-size:21px !important}

/* ---------- KPI cards ---------- */
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:var(--gap);height:var(--kpi)}
.kpi{display:flex;align-items:center;gap:14px;padding:0 18px;background:var(--card);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);min-width:0}
.kpi-i{width:46px;height:46px;border-radius:50%;display:grid;place-items:center;flex:none;background:var(--red-tint);color:var(--red)}
.kpi-i.ind{background:var(--accent-soft);color:var(--indigo)}
.kpi-b{min-width:0;flex:1}
.kpi-v{font-size:23px;font-weight:600;line-height:1.1;color:var(--text);letter-spacing:-.01em}
.kpi-l{font-size:13px;color:var(--text2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.kpi-d{text-align:right;flex:none}
.dl{font-size:13px;font-weight:600;white-space:nowrap}
.dl.up{color:var(--red)} .dl.down{color:var(--green)} .dl.flat{color:var(--text3)}
.dl-c{font-size:10.5px;color:var(--text3);margin-top:3px;white-space:nowrap}

/* ---------- panels ---------- */
div[class*="st-key-p_"]{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);padding:13px 16px 12px !important;
  display:flex !important;flex-direction:column !important;gap:6px !important;overflow:hidden;box-sizing:border-box;box-shadow:var(--shadow)}
div[class*="st-key-p_"] > [data-testid="stElementContainer"]{min-height:0}
div[class*="st-key-p_"] [data-testid="stFullScreenFrame"], div[class*="st-key-p_"] [data-testid="stPlotlyChart"]{height:100% !important;min-height:0 !important}
.ph{display:flex;align-items:center;justify-content:space-between;gap:8px;min-height:22px}
.pt{font-weight:600;font-size:15px;color:var(--text);line-height:1.25;display:flex;align-items:center;gap:7px;white-space:nowrap}
.pt .tip{color:var(--text3);cursor:help;display:inline-flex}
.ps{font-size:11.5px;color:var(--text3);line-height:1.3;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:-2px}
.fill{height:100%}

/* ---------- sidebar: brand, navigation, 3D self-folding globe ---------- */
@keyframes aegisGlobeOuter {
  0%   { transform: perspective(520px) rotateZ(0deg) rotateX(14deg) rotateY(-12deg) scale(1); }
  50%  { transform: perspective(520px) rotateZ(180deg) rotateX(-14deg) rotateY(12deg) scale(0.91); }
  100% { transform: perspective(520px) rotateZ(360deg) rotateX(14deg) rotateY(-12deg) scale(1); }
}
@keyframes aegisGlobeInner {
  0%   { transform: perspective(520px) rotateZ(360deg) rotateX(-18deg) rotateY(18deg) scale(0.84); opacity: 0.78; }
  50%  { transform: perspective(520px) rotateZ(180deg) rotateX(18deg) rotateY(-18deg) scale(1.05); opacity: 0.98; }
  100% { transform: perspective(520px) rotateZ(0deg) rotateX(-18deg) rotateY(18deg) scale(0.84); opacity: 0.78; }
}
section[data-testid="stSidebar"]{background:var(--side) !important;border-right:1px solid var(--line) !important}
@media (min-width: 1180px){ section[data-testid="stSidebar"]{width:var(--side-w) !important;min-width:var(--side-w) !important;max-width:var(--side-w) !important} }
section[data-testid="stSidebar"]{overflow:hidden}
section[data-testid="stSidebar"]::before{
  content:"";position:absolute;left:-85px;bottom:-110px;width:330px;height:330px;
  background:var(--globe) center/contain no-repeat;opacity:.82;pointer-events:none;
  transform-origin:50% 50%;animation:aegisGlobeOuter 34s linear infinite;will-change:transform;
}
section[data-testid="stSidebar"]::after{
  content:"";position:absolute;left:-85px;bottom:-110px;width:330px;height:330px;
  background:var(--globe-core) center/contain no-repeat;opacity:.92;pointer-events:none;
  transform-origin:50% 50%;animation:aegisGlobeInner 22s ease-in-out infinite;will-change:transform,opacity;
}
[data-testid="stSidebarContent"]{padding:0 !important;position:relative;z-index:1}
[data-testid="stSidebarUserContent"]{padding:22px 14px 12px !important}
[data-testid="stSidebar"] [data-testid="stVerticalBlock"]{gap:10px !important}
.brand{display:flex;gap:11px;align-items:center;padding:0 6px 18px}
.brand-name{font-size:24px;font-weight:600;letter-spacing:.02em;color:var(--text);line-height:1}
.brand-sub{font-size:12.5px;color:var(--text2);margin-top:4px;line-height:1.25;white-space:nowrap}
div.st-key-nav [data-testid="stRadioGroup"]{gap:3px;flex-direction:column}
div.st-key-nav label[data-testid="stRadioOption"]{margin:0;padding:9px 12px;border-radius:9px;cursor:pointer;display:flex;align-items:center;gap:12px;color:var(--text2);transition:background .12s}
div.st-key-nav label[data-testid="stRadioOption"]::before{width:21px;height:21px;flex:none;overflow:hidden;font-family:'Material Symbols Rounded';font-size:21px;line-height:1;
  font-feature-settings:'liga';font-variation-settings:'FILL' 0,'wght' 400,'GRAD' 0,'opsz' 24;-webkit-font-smoothing:antialiased}
div.st-key-nav label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]){display:none}
div.st-key-nav label[data-testid="stRadioOption"] p{font-size:14px;font-weight:500;color:inherit !important;white-space:nowrap}
div.st-key-nav label[data-testid="stRadioOption"]:hover{background:var(--raised);color:var(--text)}
div.st-key-nav label[data-testid="stRadioOption"]:has(input:checked){background:var(--nav-on);color:var(--nav-on-text)}
div.st-key-nav label[data-testid="stRadioOption"]:has(input:checked)::before{color:var(--nav-on-text);font-variation-settings:'FILL' 1,'wght' 400,'GRAD' 0,'opsz' 24}

/* ---------- widgets (both modes) ---------- */
[data-testid="stWidgetLabel"]{margin-bottom:2px !important;min-height:0 !important}
[data-testid="stWidgetLabel"] p{font-size:12px !important;font-weight:500 !important;color:var(--text2) !important}
div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]{background:var(--raised) !important;border:1px solid var(--line) !important;border-radius:8px !important;min-height:36px;padding-left:30px !important;max-height:62px;overflow-y:auto}
div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]:hover, div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]:focus-within{border-color:var(--line-strong) !important}
.stApp [data-testid="stMultiSelect"] input, .stApp [data-testid="stSelectbox"] input{color:var(--text) !important;font-size:12.5px !important;-webkit-text-fill-color:var(--text) !important}
.stApp [data-testid="stMultiSelect"] input::placeholder{color:var(--text2) !important;-webkit-text-fill-color:var(--text2) !important;opacity:1}
.stApp [data-testid="stMultiSelect"] button svg, .stApp [data-testid="stSelectbox"] svg{color:var(--text3) !important}
.stApp input{color:var(--text) !important;-webkit-text-fill-color:var(--text) !important;caret-color:var(--indigo)}
.stApp input::placeholder{color:var(--text3) !important;-webkit-text-fill-color:var(--text3) !important;opacity:1}
div.st-key-q input{font-size:13px !important;background:transparent !important}
.stApp [data-baseweb="select"] [aria-hidden="true"], .stApp [data-baseweb="select"] svg{color:var(--text3) !important}
.stApp [data-baseweb="select"] div[value], .stApp [data-baseweb="select"] [class*="placeholder"]{color:var(--text3) !important;font-size:12.5px !important}
[data-testid="stMultiSelectTagsContainer"] span[role="group"] > span{background:var(--accent-soft) !important;border:1px solid transparent;border-radius:6px !important;height:23px !important}
[data-testid="stMultiSelectTagsContainer"] span[role="group"] > span span{color:var(--text) !important;font-size:11.5px !important}
[data-testid="stMultiSelectTagsContainer"] span[role="group"] > span svg{color:var(--text2) !important}
.stApp [data-testid="stSelectbox"] div[role="group"]{background:var(--raised) !important;border:1px solid var(--line) !important;border-radius:8px !important;min-height:32px}
:is([data-testid="stMultiSelectDropdown"], [data-testid="stSelectboxVirtualDropdown"]){background:var(--card) !important;border:1px solid var(--line) !important;border-radius:10px !important;box-shadow:0 14px 34px rgba(0,0,0,.22) !important;min-width:250px}
:is([data-testid="stMultiSelectDropdown"], [data-testid="stSelectboxVirtualDropdown"]) [role="option"]{color:var(--text) !important;font-size:12.5px !important;background:transparent !important}
:is([data-testid="stMultiSelectDropdown"], [data-testid="stSelectboxVirtualDropdown"]) [role="option"]:is([data-focused="true"], :hover, [aria-selected="true"]){background:var(--raised) !important}
div[data-baseweb="popover"] > div, div[data-baseweb="popover"] ul{background:var(--card) !important;border-color:var(--line) !important}
div[data-baseweb="popover"] ul{border:1px solid var(--line) !important;border-radius:10px !important;box-shadow:0 12px 32px rgba(0,0,0,.25) !important}
div[data-baseweb="popover"] li{color:var(--text) !important;font-size:12.5px !important;background:transparent !important}
div[data-baseweb="popover"] li:hover, div[data-baseweb="popover"] li[aria-selected="true"]{background:var(--raised) !important}
[data-testid="stPopoverBody"]{background:var(--card) !important;border:1px solid var(--line) !important;border-radius:12px !important;color:var(--text) !important;box-shadow:0 16px 40px rgba(0,0,0,.28) !important}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] li{color:var(--text2);font-size:13px}
[data-testid="stPopoverBody"] strong{color:var(--text)}
[data-testid="stSlider"]{padding:0 6px}
[data-testid="stSlider"] [data-testid="stSliderTickBar"] p, [data-testid="stSliderTickBarMin"], [data-testid="stSliderTickBarMax"]{font-size:11.5px !important;color:var(--text2) !important}
[data-testid="stSlider"] [data-testid="stSliderThumbValue"]{font-size:11.5px;font-weight:600;color:var(--text) !important}
[data-testid="stSlider"] [role="slider"]{background:var(--card) !important;border:2px solid var(--indigo) !important;box-shadow:0 0 0 3px var(--accent-soft) !important;width:16px !important;height:16px !important}
[data-testid="stForm"]{border:0 !important;padding:0 !important;background:transparent !important}
[data-testid="stForm"] > div > [data-testid="stVerticalBlock"]{gap:9px !important}
button[data-testid^="stBaseButton-primary"]{background:linear-gradient(90deg, var(--indigo), var(--violet)) !important;border:0 !important;color:#fff !important;border-radius:9px !important;min-height:40px;font-weight:600 !important;box-shadow:0 6px 16px rgba(109,94,246,.30)}
button[data-testid^="stBaseButton-primary"] p, button[data-testid^="stBaseButton-primary"] span{color:#fff !important;font-weight:600 !important;font-size:13.5px !important}
button[data-testid^="stBaseButton-primary"]:hover{filter:brightness(1.08)}
button[data-testid^="stBaseButton-secondary"], [data-testid="stDownloadButton"] button{background:var(--raised) !important;border:1px solid var(--line) !important;color:var(--text2) !important;border-radius:8px !important;min-height:30px !important;padding:2px 12px !important}
button[data-testid^="stBaseButton-secondary"] p, [data-testid="stDownloadButton"] button p{font-size:12px !important;color:inherit !important}
button[data-testid^="stBaseButton-secondary"]:hover:not(:disabled), [data-testid="stDownloadButton"] button:hover{border-color:var(--line-strong) !important;color:var(--text) !important}
button[data-testid^="stBaseButton-secondary"]:disabled{opacity:.4}
button[data-testid="stBaseButton-tertiary"]{color:var(--red) !important;padding:0 !important;min-height:0 !important;background:transparent !important}
button[data-testid="stBaseButton-tertiary"] p{font-size:13px !important;font-weight:600 !important;color:var(--red) !important}
button[data-testid="stBaseButton-tertiary"]:disabled p{color:var(--text3) !important}
[data-testid="stToast"]{background:var(--card) !important;border:1px solid var(--line) !important;color:var(--text) !important}
[data-testid="stTooltipContent"]{background:var(--card) !important;color:var(--text) !important;border:1px solid var(--line)}
/* segmented radios (map metric, page switches, theme) */
div[class*="st-key-seg_"] [data-testid="stRadioGroup"]{gap:0;flex-wrap:nowrap;background:var(--raised);border:1px solid var(--line);border-radius:9px;padding:2px;width:max-content;margin-left:auto}
div[class*="st-key-seg_"] label[data-testid="stRadioOption"]{margin:0;padding:3px 9px;border-radius:7px;cursor:pointer}
div[class*="st-key-seg_"] label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]){display:none}
div[class*="st-key-seg_"] label[data-testid="stRadioOption"] p{font-size:12px;font-weight:500;color:var(--text2) !important;white-space:nowrap}
div[class*="st-key-seg_"] label[data-testid="stRadioOption"]:has(input:checked){background:var(--card);box-shadow:0 1px 3px rgba(0,0,0,.18)}
div[class*="st-key-seg_"] label[data-testid="stRadioOption"]:has(input:checked) p{color:var(--text) !important}
div[class*="st-key-phdr"] [data-testid="stHorizontalBlock"]{align-items:center !important;flex-wrap:nowrap !important;gap:8px !important}
div[class*="st-key-phdr"]{flex:0 0 auto !important;height:auto !important}

/* ---------- filters card ---------- */
div.st-key-p_filters{gap:10px !important}
div.st-key-p_filters [data-testid="stHorizontalBlock"]{align-items:center !important;flex-wrap:nowrap !important}
div.st-key-p_filters [data-testid="stColumn"]:last-child{display:flex;justify-content:flex-end}
.fl-note{font-size:11px;color:var(--text3);line-height:1.35}

/* ---------- key insights ---------- */
.ins{display:flex;flex-direction:column}
.ins-i{display:flex;gap:12px;align-items:flex-start;padding:13px 0;border-top:1px solid var(--line)}
.ins-i:first-child{border-top:0;padding-top:4px}
.ins-ic{width:40px;height:40px;border-radius:10px;border:1px solid var(--line);background:var(--raised);display:grid;place-items:center;flex:none;color:var(--indigo)}
.ins-ic.bad{color:var(--red)} .ins-ic.good{color:var(--green)}
.ins-v{font-size:16px;font-weight:600;color:var(--red);line-height:1.15}
.ins-v.good{color:var(--green)} .ins-v.neutral{color:var(--text)}
.ins.grouped{overflow-y:auto;padding-right:4px;margin-right:-6px}
.ins.grouped .ins-i{padding:9px 0}
.ins.grouped .ins-ic{width:34px;height:34px} .ins.grouped .ins-ic .ms{font-size:18px !important}
.ins.grouped .ins-v{font-size:15px}
.ins-h{display:flex;align-items:center;gap:6px;font-size:10.5px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text3);
  padding:10px 0 2px;position:sticky;top:0;background:var(--card);z-index:1}
.ins-h:first-child{padding-top:0}
.ins.grouped .ins-h + .ins-i{border-top:0}
.ps.pi{display:flex;align-items:center;gap:5px;color:var(--text2);margin-top:1px}
.ps.pi .ms{color:var(--yellow);flex:none}
.ps.pi span{overflow:hidden;text-overflow:ellipsis}
.ins-t{font-size:12px;color:var(--text2);line-height:1.35;margin-top:2px}

/* ---------- donut + legend ---------- */
.donut{display:flex;align-items:center;gap:10px;height:100%}
.donut svg{flex:none}
.dn{position:relative;flex:none}
.dn img{display:block}
.dn-t{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none}
.dn-t b{font-size:20px;font-weight:600;color:var(--text);line-height:1.1}
.dn-t span{font-size:11.5px;color:var(--text2)}
.lg{display:flex;flex-direction:column;gap:7px;flex:1;min-width:0}
.lg-r{display:flex;align-items:center;gap:7px;font-size:11px;color:var(--text2);min-width:0}
.lg-r i{width:9px;height:9px;border-radius:50%;flex:none}
.lg-r span:first-of-type{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lg-r b{font-weight:600;color:var(--text)}

/* ---------- bar list ---------- */
.bars{display:flex;flex-direction:column;justify-content:space-around;height:100%;gap:6px}
.bar{display:grid;grid-template-columns:minmax(70px, 40%) 1fr auto;align-items:center;gap:10px;font-size:12px;color:var(--text2)}
.bar span:first-child{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--text)}
.bar-t{height:12px;border-radius:6px;background:var(--track);overflow:hidden}
.bar-t i{display:block;height:100%;border-radius:6px;background:linear-gradient(90deg, var(--red-deep), var(--red) 70%, var(--red-soft))}
.bar b{font-weight:600;color:var(--text);min-width:44px;text-align:right}

/* ---------- human impact ---------- */
.hi{display:flex;flex-direction:column;gap:12px;height:100%;justify-content:space-between}
.hi-tiles{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.hi-t{border:1px solid var(--line);border-radius:10px;padding:9px 10px;display:flex;gap:8px;align-items:flex-start;background:var(--raised);min-width:0}
.hi-t > div:last-child{min-width:0}
.hi-v{font-size:15px;font-weight:600;color:var(--text);line-height:1.15;white-space:nowrap}
.hi-l{font-size:11.5px;color:var(--text2)}
.split{height:13px;border-radius:7px;overflow:hidden;display:flex;background:var(--track)}
.split i:first-child{background:var(--red)} .split i:last-child{background:var(--red-soft)}
.split-l{display:flex;gap:18px;font-size:12px;color:var(--text2)}
.split-l span{display:flex;align-items:center;gap:7px}
.split-l i{width:11px;height:11px;border-radius:3px}

/* ---------- tables ---------- */
.tbl-w{height:100%;overflow:auto}
table.tbl{width:100%;border-collapse:collapse;font-size:12px}
table.tbl th{position:sticky;top:0;background:var(--card);text-align:left;font-weight:600;color:var(--text3);font-size:11px;text-transform:uppercase;letter-spacing:.04em;padding:6px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
table.tbl{table-layout:auto}
table.tbl td{padding:6px 8px;border-bottom:1px solid var(--line);color:var(--text2);white-space:nowrap;max-width:150px;overflow:hidden;text-overflow:ellipsis}
table.tbl td.w{max-width:170px}
table.tbl td.n, table.tbl th.n{text-align:right;font-variant-numeric:tabular-nums}
table.tbl td b{color:var(--text);font-weight:600}
table.tbl tr:hover td{background:var(--raised)}
.pill{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;background:var(--red-tint);color:var(--red);font-weight:600}
.meter{height:6px;border-radius:3px;background:var(--track);overflow:hidden;min-width:60px}
.meter i{display:block;height:100%;border-radius:3px;background:var(--red)}

/* ---------- statistics cards ---------- */
.sc{display:flex;flex-direction:column;height:100%;gap:7px;overflow:hidden}
.sc-h{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.sc-name{font-weight:600;font-size:14.5px;color:var(--text);white-space:nowrap}
.sc-q{font-size:12px;color:var(--text2);margin-top:2px}
.badge{font-size:11px;font-weight:600;border-radius:999px;padding:3px 9px;white-space:nowrap;background:var(--raised);color:var(--text2)}
.badge.yes{color:var(--green);background:rgba(34,197,94,.12)}
.badge.no{color:var(--orange);background:rgba(249,123,61,.12)}
.sc-e{display:flex;align-items:baseline;gap:10px;margin-top:2px}
.sc-ev{font-size:34px;font-weight:600;line-height:1;color:var(--text);letter-spacing:-.01em}
.sc-en{font-size:12px;color:var(--text2)}
.gauge{position:relative;height:6px;border-radius:3px;background:var(--track);margin:2px 0 1px}
.gauge i{position:absolute;top:0;bottom:0;border-radius:3px;background:linear-gradient(90deg, var(--indigo), var(--violet))}
.gauge u{position:absolute;top:-3px;bottom:-3px;width:1px;background:var(--line-strong)}
.gscale{display:flex;justify-content:space-between;font-size:10.5px;color:var(--text3)}
.sc-r{font-size:13.5px;line-height:1.4;color:var(--text);margin:3px 0 0}
.sc-f{margin-top:auto;display:flex;flex-wrap:wrap;gap:4px 14px;font-size:11.5px;color:var(--text3)}
.sc-f b{color:var(--text2);font-weight:600}
div[class*="st-key-p_s_"] [data-testid="stHorizontalBlock"]{gap:22px !important}
.mh{font-size:12.5px;font-weight:600;color:var(--text)}
.mh-s{font-size:11px;color:var(--text3);margin-top:1px}
.pairs{display:flex;flex-direction:column;margin-top:4px}
.pair{display:grid;grid-template-columns:1fr auto;gap:3px 8px;padding:6px 0 6px;border-top:1px solid var(--line);align-items:baseline}
.pair-l{font-size:12px;color:var(--text2);line-height:1.25}
.pair-l b{color:var(--text);font-weight:600}
.pair-v{font-size:11px;color:var(--text3);text-align:right;white-space:nowrap}
.pair-v span{font-size:18px;font-weight:600;color:var(--red);margin-right:6px}
.pair .meter{grid-column:1 / -1}

/* ---------- comparison tiles, definitions, coverage ---------- */
.cmp{display:grid;grid-template-columns:1fr 1fr;gap:10px;height:100%}
.cmp-c{border:1px solid var(--line);border-radius:10px;padding:11px 13px;display:flex;flex-direction:column;gap:4px;background:var(--raised)}
.cmp-t{font-size:13px;font-weight:600;color:var(--text)}
.cmp-s{font-size:11px;color:var(--text3)}
.cmp-v{font-size:28px;font-weight:600;line-height:1.05;color:var(--red);margin-top:4px}
.cmp-l{font-size:11px;color:var(--text2)}
.cmp-r{display:flex;justify-content:space-between;font-size:12px;color:var(--text2);padding-top:5px;border-top:1px solid var(--line);margin-top:3px}
.cmp-r b{color:var(--text);font-weight:600}
.defs{font-size:12.5px;line-height:1.5;color:var(--text2);overflow:auto;height:100%;margin:0 !important;padding:0 !important}
.defs dt, .defs dd{margin-left:0 !important;padding-left:0 !important}
.defs dt{color:var(--text);font-weight:600;margin-top:8px}
.defs dt:first-child{margin-top:0}
.defs dd{margin:1px 0 0}
.cov-r{display:flex;justify-content:space-between;font-size:12px;color:var(--text2);margin-top:9px}
.cov-r b{color:var(--text);font-weight:600}
.cov .meter{margin-top:5px}
.cov .meter i{background:linear-gradient(90deg, var(--indigo), var(--violet))}

/* ---------- empty, error, footer ---------- */
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px;height:100%;text-align:center;padding:30px}
.empty .big{font-size:22px;font-weight:600;color:var(--text)}
.empty .sm{font-size:13px;color:var(--text2);max-width:440px;line-height:1.45}
.foot{height:var(--foot);display:flex;align-items:center;font-size:11px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}

/* ---------- maps: legend beside the map, zoom buttons bottom left ---------- */
div.st-key-p_map{position:relative}
.mlg{position:absolute;right:16px;bottom:16px;display:flex;flex-direction:column;gap:7px;font-size:11.5px;color:var(--text2);z-index:3;pointer-events:none}
.mlg div{display:flex;align-items:center;gap:8px;white-space:nowrap}
.mlg i{width:13px;height:13px;border-radius:3px;flex:none}
div[class*="st-key-p_"] [data-testid="stElementContainer"]:has(.mlg){position:static;height:0;min-height:0;margin-top:-6px !important}
div.st-key-p_map > [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){width:calc(100% - 112px) !important}
@container (max-width: 430px){
  div.st-key-p_map > [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){width:100% !important;margin-bottom:24px !important}
  .mlg{flex-direction:row;flex-wrap:wrap;justify-content:flex-end;left:16px;right:14px;bottom:9px;gap:3px 10px;font-size:10.5px}
  .mlg i{width:10px;height:10px}
}
.js-plotly-plot .plotly .modebar{background:transparent !important}
div.st-key-p_map .modebar-container{top:auto !important;bottom:8px;height:auto !important}
div.st-key-p_map .modebar{position:absolute;left:4px !important;right:auto !important;bottom:0;top:auto !important;opacity:1 !important}
div.st-key-p_map .modebar-group{display:flex !important;flex-direction:column;gap:6px;background:transparent !important;padding:0 !important}
div.st-key-p_map .modebar-btn{width:28px;height:28px;display:grid !important;place-items:center;border-radius:7px;background:var(--card) !important;border:1px solid var(--line-strong)}
div.st-key-p_map .modebar-btn path{fill:var(--text2) !important}
div.st-key-p_map .modebar-btn:hover path{fill:var(--text) !important}

/* ---------- short screens: drop extras ---------- */
@media (min-width: 1180px) and (max-height: 760px){
  .ins-i{padding:9px 0} .ins-ic{width:34px;height:34px}
  .ps:not(.pi){display:none}
}
@media (min-width: 1180px){
  /* the filters column keeps a usable width whatever the window size */
  div.st-key-body > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child{flex:0 0 clamp(196px, 14vw, 232px) !important;width:auto !important}
  div.st-key-body > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child{flex:1 1 0 !important;width:auto !important}
}
@media (max-width: 1440px) and (min-width: 1180px){
  :root{--side-w:196px;--kpi:66px}
  .kpi{padding:0 12px;gap:10px} .kpi-i{width:38px;height:38px} .kpi-i .ms{font-size:20px !important} .kpi-v{font-size:19px} .kpi-l{font-size:12px}
  .dl{font-size:12px} .dl-c{font-size:10px}
  .ttl{font-size:22px} .sub{font-size:12px}
  .brand-name{font-size:21px}
  div.st-key-hdr [data-testid="stColumn"]:first-child{flex:1 1 0 !important;width:auto !important}
  div.st-key-hdr [data-testid="stColumn"]:nth-child(2){flex:0 1 260px !important;width:auto !important}
  div.st-key-nav label[data-testid="stRadioOption"] p{font-size:13.5px}
  div.st-key-nav label[data-testid="stRadioOption"]{padding:8px 10px;gap:10px}
}
@media (max-height: 820px) and (min-width: 1180px){
  :root{--head:48px;--gap:10px}
  div.st-key-p_filters{gap:6px !important;padding:11px 13px 10px !important}
  div.st-key-p_filters div[data-testid="stVerticalBlock"]{gap:5px !important}
  div[class*="st-key-f_"] [data-testid="stMultiSelect"] div[role="group"]{min-height:32px}
  div.st-key-p_filters [data-testid="stWidgetLabel"] p{font-size:11.5px !important}
  div.st-key-p_filters button[data-testid^="stBaseButton-primary"]{min-height:34px}
  div.st-key-p_filters .fl-note{display:none}
  [data-testid="stSidebarUserContent"]{padding-top:16px !important}
}
/* panels adapt to their own width (container queries), not just the window */
div[class*="st-key-p_"]{container-type:inline-size}
@container (max-width: 196px){
  .hi-t .kpi-i{display:none} .hi-t{padding:8px 9px} .hi-v{font-size:14.5px} .hi-tiles{gap:6px}
  .split-l{flex-direction:column;gap:3px}
}
@container (max-width: 236px){
  .lg-r{font-size:10.5px} .donut{gap:8px}
  .dn{width:80px !important;height:80px !important} .dn img{width:80px;height:80px} .dn-t b{font-size:13px !important} .dn-t span{font-size:9.5px}
  div[class*="st-key-p_"]{padding-left:13px !important;padding-right:13px !important}
}
@container (max-width: 196px){
  .ins-ic{width:32px;height:32px} .ins-ic .ms{font-size:17px !important} .ins-i{gap:9px}
}
@container (max-width: 140px){
  .ins-ic{display:none}
}

/* ---------- below 1180px: a wrapping, scrolling layout ---------- */
@media (max-width: 1179.98px){
  header[data-testid="stHeader"]{background:transparent !important;height:2.6rem}
  [data-testid="stSidebarHeader"]{padding:10px 12px 0 !important;height:auto}
  [data-testid="stMainBlockContainer"]{padding:46px 14px 14px !important}
  div.st-key-hdr [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;row-gap:8px}
  div.st-key-hdr [data-testid="stColumn"]{flex:0 0 auto !important;width:auto !important}
  div.st-key-hdr [data-testid="stColumn"]:first-child{flex:1 1 100% !important;width:100% !important}
  div.st-key-hdr [data-testid="stColumn"]:nth-child(2){flex:1 1 200px !important}
  .ttl{font-size:22px;white-space:normal}
  .kpis{grid-template-columns:repeat(auto-fit, minmax(210px, 1fr));height:auto}
  .kpi{padding:12px 14px}
  :is(div.st-key-body, div[class*="st-key-row_"]) [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;row-gap:var(--gap)}
  :is(div.st-key-body, div[class*="st-key-row_"]) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{flex:1 1 calc(50% - var(--gap)) !important;min-width:300px !important}
  div.st-key-body > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{flex:1 1 100% !important}
  div[class*="st-key-p_"] [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){height:300px !important}
  div.st-key-p_map [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){height:380px !important}
  div[class*="st-key-p_s_"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{flex:1 1 260px !important;min-width:260px !important}
  div[class*="st-key-p_s_"] [data-testid="stElementContainer"]:has([data-testid="stPlotlyChart"]){height:240px !important}
  div[class*="st-key-p_"]{min-height:220px}
  div[class*="st-key-p_"] .fill{height:auto;min-height:200px}
  .tbl-w{max-height:420px}
  .ps, .sub{white-space:normal}
  .foot{height:auto;white-space:normal;padding:4px 0}
}
@media (max-width: 640px){
  :is(div.st-key-body, div[class*="st-key-row_"]) [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]{flex:1 1 100% !important;min-width:0 !important}
  .cmp, .hi-tiles{grid-template-columns:1fr}
}
"""

# Row split (share of the body height taken by the top row) per page.
ROW_SPLIT = {"Overview": 0.53, "Incidents": 0.46, "Groups": 0.5, "Regions": 0.58, "Trends": 0.52,
             "Human Impact": 0.5, "Analysis": 0.5, "Data & Methods": 0.5}


def css_block(page: str, mode: str) -> str:
    """The full <style> block for a page in a colour mode."""
    body = ("calc(100vh - var(--pad-t) - var(--pad-b) - var(--head) - var(--kpi) - var(--foot) - var(--gap) * 3)")
    local = f":root{{--body:{body};--fa:{ROW_SPLIT.get(page, 0.5)}}}"
    return (f"<style>{font_face_css()}{_root_vars(mode)}{local}{BASE_CSS}{_nav_icon_css()}{_filter_icon_css()}</style>")


# --------------------------------------------------------------------------------------
# HTML builders
# --------------------------------------------------------------------------------------
def brand_html() -> str:
    return (f'<div class="brand">{_shield()}<div><div class="brand-name">AEGIS</div>'
            '<div class="brand-sub">Global Terrorism<br/>Dashboard</div></div></div>')


def title_html(title: str, subtitle: str) -> str:
    return f'<div class="ttl">{esc(title)}</div><div class="sub">{esc(subtitle)}</div>'


def kbd_html() -> str:
    return '<span class="kbd">Ctrl K</span>'


def info_tip(text: str) -> str:
    return f'<span class="tip" title="{esc(text)}">{icon("info", 15)}</span>' if text else ""


def panel_header(title: str, info: str = "", subtitle: str = "", right: str = "", insight: dict | None = None) -> str:
    sub = f'<div class="ps">{esc(subtitle)}</div>' if subtitle else ""
    if insight:
        sub += (f'<div class="ps pi {insight.get("tone", "neutral")}" title="{esc(insight["line"])}">'
                f'{icon("bulb", 14, filled=True)}<span>{esc(insight["line"])}</span></div>')
    return f'<div class="ph"><div class="pt">{esc(title)}{info_tip(info)}</div>{right}</div>{sub}'


def delta_html(pct: float | None, caption: str, good_when_down: bool = True) -> str:
    """Change badge: increases in harm are red, decreases green (the dashboard counts harm, so down is good)."""
    if _missing(pct):
        return f'<div class="dl flat">no comparison</div><div class="dl-c">{esc(caption)}</div>'
    cls = "flat" if abs(pct) < 0.05 else ("up" if (pct > 0) == good_when_down else "down")
    arrow = "&#8593;" if pct > 0 else "&#8595;" if pct < 0 else "&#8594;"
    return f'<div class="dl {cls}">{arrow} {esc(fmt_delta(pct))}</div><div class="dl-c">{esc(caption)}</div>'


def kpi_cards(items: list[dict]) -> str:
    """items: {icon, value, label, delta, caption, tip, indigo}"""
    cells = []
    for it in items:
        cls = "kpi-i ind" if it.get("indigo") else "kpi-i"
        cells.append(f'<div class="kpi" title="{esc(it.get("tip", ""))}"><div class="{cls}">{icon(it["icon"], 24, filled=True)}</div>'
                     f'<div class="kpi-b"><div class="kpi-v">{esc(it["value"])}</div><div class="kpi-l">{esc(it["label"])}</div></div>'
                     f'<div class="kpi-d">{delta_html(it.get("delta"), it.get("caption", ""))}</div></div>')
    return '<div class="kpis">' + "".join(cells) + "</div>"


def _insight_row(it: dict) -> str:
    tone = it.get("tone", "bad")
    return (f'<div class="ins-i"><div class="ins-ic {tone}">{icon(it["icon"], 20)}</div>'
            f'<div><div class="ins-v {tone}">{esc(it["value"])}</div><div class="ins-t">{esc(it["text"])}</div></div></div>')


def insights_html(items: list[dict], grouped: bool = False) -> str:
    """Key insights: icon tile, value, sentence. Grouped lists get a heading per topic and scroll inside the panel."""
    if not grouped:
        return '<div class="ins fill">' + "".join(_insight_row(it) for it in items) + "</div>"
    parts, topic = [], None
    for it in items:
        if it["topic"] != topic:
            topic = it["topic"]
            parts.append(f'<div class="ins-h">{icon(TOPIC_ICON.get(topic, "bulb"), 14)}{esc(topic)}</div>')
        parts.append(_insight_row(it))
    return '<div class="ins grouped fill">' + "".join(parts) + "</div>"


def donut_html(rows: list[tuple[str, int, float]], total: int, colors: list[str], track: str, center_label: str = "Incidents",
               size: int = 150) -> str:
    """Donut (one arc per row) with a legend; rows are (label, count, percent)."""
    r, w = size / 2 - 12, 22
    circ = 2 * np.pi * r
    arcs, offset = [], 0.0
    for (_, _, pct), color in zip(rows, colors, strict=False):
        length = circ * pct / 100
        gap = 2 if len(rows) > 1 and length > 4 else 0
        arcs.append(f'<circle cx="{size / 2}" cy="{size / 2}" r="{r:.1f}" fill="none" stroke="{color}" stroke-width="{w}" '
                    f'stroke-dasharray="{max(length - gap, 0):.2f} {circ:.2f}" stroke-dashoffset="{-offset:.2f}" '
                    f'transform="rotate(-90 {size / 2} {size / 2})"/>')
        offset += length
    ring = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}">'
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{r:.1f}" fill="none" stroke="{track}" stroke-width="{w}"/>{"".join(arcs)}</svg>')
    alt = f"{center_label} by type: " + ", ".join(f"{lab} {pct:.1f}%" for lab, _, pct in rows)
    svg = (f'<div class="dn" style="width:{size}px;height:{size}px">{_img(ring, size, size, alt=alt)}'
           f'<div class="dn-t"><b style="font-size:{size * 0.15:.0f}px">{total:,}</b><span>{esc(center_label)}</span></div></div>')
    legend = "".join(f'<div class="lg-r" data-filter-val="{esc(label)}" style="cursor:pointer" title="{esc(label)}: {n:,}"><i style="background:{c}"></i><span>{esc(label)}</span><b>{pct:.1f}%</b></div>'
                     for (label, n, pct), c in zip(rows, colors, strict=False))
    return f'<div class="donut fill">{svg}<div class="lg">{legend}</div></div>'


def bars_html(rows: list[tuple[str, str, float, str]]) -> str:
    """Horizontal bar list; rows are (label shown, full label, value, value text)."""
    if not rows:
        return '<div class="empty fill"><div class="sm">Nothing to rank in this selection.</div></div>'
    top = max(v for _, _, v, _ in rows) or 1
    items = "".join(f'<div class="bar" data-filter-val="{esc(full)}" style="cursor:pointer" title="{esc(full)}: {esc(txt)}"><span>{esc(lab)}</span>'
                    f'<div class="bar-t"><i style="width:{max(100 * v / top, 1.5):.1f}%"></i></div><b>{esc(txt)}</b></div>'
                    for lab, full, v, txt in rows)
    return f'<div class="bars fill">{items}</div>'


def human_impact_html(injured: int | None, killed: int | None, d_inj, d_kill, caption: str, cov_inj: str, cov_kill: str) -> str:
    total = (injured or 0) + (killed or 0)
    k_share = 100 * (killed or 0) / total if total else 0
    tiles = [("casualties", fmt_int(injured), "Injured", d_inj, cov_inj, "ind"), ("fatalities", fmt_int(killed), "Killed", d_kill, cov_kill, "")]
    t = "".join(f'<div class="hi-t" title="{esc(cov)}"><div class="kpi-i {cls}" style="width:30px;height:30px">{icon(ic, 17, filled=True)}</div>'
                f'<div><div class="hi-v">{esc(v)}</div><div class="hi-l">{esc(lab)}</div>{delta_html(d, caption)}</div></div>'
                for ic, v, lab, d, cov, cls in tiles)
    return (f'<div class="hi fill"><div class="hi-tiles">{t}</div>'
            f'<div><div class="split"><i style="width:{k_share:.1f}%"></i><i style="width:{100 - k_share:.1f}%"></i></div></div>'
            f'<div class="split-l"><span><i style="background:var(--red)"></i>Killed ({k_share:.1f}%)</span>'
            f'<span><i style="background:var(--red-soft)"></i>Injured ({100 - k_share:.1f}%)</span></div></div>')


def map_legend_html(classes: list[tuple[float, float, str, str]]) -> str:
    rows = "".join(f'<div><i style="background:{color}"></i>{esc(label)}</div>' for *_, label, color in classes)
    return f'<div class="mlg">{rows}</div>'


def table_html(columns: list[tuple[str, str]], rows: list[list[str]]) -> str:
    """columns: (title, 'n' for numeric or ''); cells are pre-escaped HTML."""
    head = "".join(f'<th class="{c}">{esc(t)}</th>' for t, c in columns)
    body = "".join("<tr>" + "".join(f'<td class="{c}">{cell}</td>' for (_, c), cell in zip(columns, row, strict=True)) + "</tr>"
                   for row in rows)
    return f'<div class="tbl-w fill"><table class="tbl"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def meter_html(frac: float) -> str:
    return f'<div class="meter"><i style="width:{100 * max(min(frac, 1), 0):.1f}%"></i></div>'


def coverage_html(rows: list[tuple[str, float | None, str]]) -> str:
    out = []
    for label, frac, tip in rows:
        pct = 0.0 if frac is None else 100 * frac
        out.append(f'<div title="{esc(tip)}"><div class="cov-r"><span>{esc(label)}</span><b>{"n/a" if frac is None else f"{pct:.1f}%"}</b></div>'
                   f'<div class="meter"><i style="width:{pct:.1f}%"></i></div></div>')
    return '<div class="cov fill">' + "".join(out) + "</div>"


def definitions_html(items: list[tuple[str, str]]) -> str:
    return '<dl class="defs fill">' + "".join(f"<dt>{esc(t)}</dt><dd>{esc(d)}</dd>" for t, d in items) + "</dl>"


def gauge_html(value: float, lo: float, hi: float) -> str:
    span = hi - lo
    pos = lambda x: 100 * (x - lo) / span
    if lo < 0:  # bipolar: fill from zero
        a, b = sorted((pos(0), pos(value)))
        zero = f'<u style="left:{pos(0):.1f}%"></u>'
    else:
        a, b, zero = 0, pos(value), ""
    scale = f'<div class="gscale"><span>{lo:g}</span><span>{hi:g}</span></div>'
    return f'<div class="gauge">{zero}<i style="left:{a:.1f}%;width:{max(b - a, 0.8):.1f}%"></i></div>{scale}'


def stat_card_html(r, reading: str) -> str:
    if not r.ok:
        return (f'<div class="sc"><div class="sc-h"><div class="sc-name">{esc(r.name)}</div><span class="badge">not run</span></div>'
                f'<div class="sc-q">{esc(r.question)}</div><p class="sc-r">{esc(r.note or "Not enough data in this selection.")}</p></div>')
    sig = r.p_holm is not None and r.p_holm < 0.05
    badge = ('<span class="badge yes">Significant (Holm)</span>' if sig else '<span class="badge no">Not significant (Holm)</span>')
    foot = [f"<span>n = <b>{r.n:,}</b></span>", f"<span>{esc(r.stat_name)} = <b>{r.statistic:,.3f}</b></span>",
            f"<span>Holm-adjusted p <b>{fmt_p(r.p_holm)}</b></span>"]
    if r.note:
        foot.append(f"<span>{esc(r.note)}</span>")
    return (f'<div class="sc"><div class="sc-h"><div class="sc-name">{esc(r.name)}</div>{badge}</div>'
            f'<div class="sc-q">{esc(r.question)}</div>'
            f'<div class="sc-e"><span class="sc-ev">{r.effect:+.3f}</span><span class="sc-en">{esc(r.effect_name)}</span></div>'
            f'{gauge_html(r.effect, r.effect_lo, r.effect_hi)}'
            f'<p class="sc-r">{esc(reading)}</p><div class="sc-f">{"".join(foot)}</div></div>')


def mini_header(title: str, subtitle: str = "") -> str:
    sub = f'<div class="mh-s">{esc(subtitle)}</div>' if subtitle else ""
    return f'<div><div class="mh">{esc(title)}</div>{sub}</div>'


def pairs_html(pairs) -> str:
    """Most over-represented attack/target pairs: (attack label, target label, observed/expected, observed)."""
    head = mini_header("Most over-represented pairs", "Observed divided by expected under independence, pairs with 200+ incidents")
    if not pairs:
        return head + '<div class="fl-note">No attack and target pair has 200 or more incidents in this selection.</div>'
    top = max(p[2] for p in pairs)
    rows = "".join(
        f'<div class="pair"><div class="pair-l"><b>{esc(a)}</b> on {esc(t)}</div>'
        f'<div class="pair-v"><span>{ratio:.1f}×</span>{obs:,} incidents</div>{meter_html(ratio / top)}</div>'
        for a, t, ratio, obs in pairs)
    return head + f'<div class="pairs">{rows}</div>'


def compare_html(t) -> str:
    cards = []
    for name, row in t.iterrows():
        cards.append(
            f'<div class="cmp-c"><div class="cmp-t">{esc(name)}</div>'
            f'<div class="cmp-s">{int(row["incidents"]):,} incidents ({fmt_pct(row["share"])} of the selection)</div>'
            f'<div class="cmp-v">{fmt_num(row["fatal_mean"])}</div><div class="cmp-l">mean reported fatalities per incident</div>'
            f'<div class="cmp-r"><span>Median fatalities</span><b>{fmt_num(row["fatal_median"], 0)}</b></div>'
            f'<div class="cmp-r"><span>Incidents with 10+ fatalities</span><b>{fmt_pct(row["fatal_ge10"])}</b></div>'
            f'<div class="cmp-r"><span>Mean reported injuries</span><b>{fmt_num(row["injury_mean"])}</b></div>'
            f'<div class="cmp-r"><span>Fatality count known for</span><b>{int(row["fatal_known"]):,}</b></div></div>')
    return '<div class="cmp fill">' + "".join(cards) + "</div>"


def empty_html(msg: str, title: str = "No incidents match these filters") -> str:
    return f'<div class="empty fill"><div class="big">{esc(title)}</div><div class="sm">{esc(msg)}</div></div>'


def error_html(what: str) -> str:
    return ('<div class="empty err fill"><div class="big">This panel could not be drawn</div>'
            f'<div class="sm">{esc(what)}: the error has been logged. The rest of the view is unaffected.</div></div>')


def footer_html(text: str) -> str:
    return f'<div class="foot">{esc(text)}</div>'

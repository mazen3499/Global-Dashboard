# Third-party assets bundled with the dashboard

| Asset | Source | Licence |
|---|---|---|
| `static/fonts/instrument-sans-*.woff2` (served by Streamlit static serving) | Instrument Sans (Instrument), via the Fontsource npm packages | SIL Open Font License 1.1 |
| `world_110m_countries.json` | Natural Earth 1:110m admin-0 countries, decoded from the `world-atlas` 2.0.2 `countries-110m.json` TopoJSON by `scripts/build_assets.py` (Antarctica removed, GTD country labels added) | Natural Earth: public domain. `world-atlas`: ISC |
| `static/globe-dark.svg`, `static/globe-light.svg` | Drawn by `scripts/build_assets.py` from the same country outlines | as above |

All are stored locally so that the dashboard makes no external network request at run time.

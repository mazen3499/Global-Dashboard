# Global Terrorism Data Analysis: Trends, Patterns, and Human Impact

An interactive Streamlit dashboard for the graduation project. It covers **111,855 incidents from 2000 to 2017**
and works on the **30 analysis columns** selected in the notebook (`Global_Terrorism_Dataset2.ipynb`, section 3).

![Overview](docs/screenshots/overview_1440x900.png)

Every figure on screen is computed with pandas from `global_cleaned.csv` (read from a lossless Parquet copy, see
*Data files*) and re-calculates when a filter changes.
Nothing is hard-coded, and nothing leaves your machine: no API key, no tile server, no CDN. The browser only talks to
the local Streamlit server.

## Run it

Python 3.12 or newer (tested on 3.12 in CI and 3.14 locally).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501. The data is read once (about 0.2 s) and cached.
`GTD_DATA_PATH=/other/path.csv streamlit run app.py` points the app at a different copy of the data (CSV or Parquet).

### Data files

The app reads `data/gtd_cleaned.parquet` (5.3 MB, committed). It is a lossless copy of `global_cleaned.csv`
(50 MB, not in git) made by `python scripts/build_data.py`, which also records the CSV's SHA-256 in
`data/gtd_cleaned.meta.json`. If a `global_cleaned.csv` next to `app.py` no longer matches that hash, the app reads the
CSV instead and logs a warning; rebuild the Parquet file to clear it.

### Development

```bash
pip install -r requirements-dev.txt
python -m playwright install chromium   # once, for the layout tests
ruff check .
pytest -m "not e2e"                     # data, KPIs, statistics, HTML builders, the app headless (about 12 s)
pytest -m e2e                           # layout in Chromium at 6 window sizes (about 80 s)
python validate.py                      # the human-readable validation report (60 checks)
python scripts/screenshots.py           # regenerate docs/screenshots
```

CI (`.github/workflows/ci.yml`) runs ruff and the tests on Python 3.12 and 3.14, then the Chromium layout tests.
The latest validation output is in `docs/validation_report.txt`.

## The five views

Every view fits one desktop screen with no page scroll. Global filters (years, region, country, attack type,
target type) sit in the left rail and drive every KPI and chart in every view.

| View | What it shows |
|---|---|
| Overview | KPI band with sparklines and data coverage, incidents and reported fatalities per year, world map, attack types, most affected countries, key findings written from the current selection |
| Geography | Map with a switch between incidents, fatalities and injuries, countries and regions (incidents beside reported fatalities), volume versus lethality |
| Attacks | Attack, target and weapon types, attack-by-target heatmap, most active groups |
| Human impact | Reported fatalities and injuries by year, share of incidents versus share of fatalities by band, casualties by attack type, suicide versus other attacks |
| Statistics | The four tests of the notebook (Spearman, chi-square, Mann-Whitney U, Kruskal-Wallis) recomputed on the current selection, with effect sizes, Holm adjustment and a plain-language reading |

## Design concept

The approved concept is **B, Dark Intelligence**: a left filter rail, a slim top bar with navigation, and a grid of
panels. The world map is the single bold element; everything else stays quiet. Colour is reserved for meaning.

| Token | Value | Use |
|---|---|---|
| Page / rail | `#070B12` / `#080D15` | backgrounds |
| Panel / raised | `#0E1520` / `#141E2D` | cards, inputs |
| Hairline / rule | `#1B2636` / `#2A3B52` | borders |
| Text | `#EAE7DF`, `#98A3B5`, `#66758B` | primary, secondary, tertiary |
| Cyan `#56CCF2` | incidents | |
| Rose `#F06A6A` | reported fatalities | |
| Amber `#F2B24A` | reported injuries | |
| Jade `#3DD9A5` | success rate | |
| Steel `#9FB0C9` | neutral, countries | |

Typography: Instrument Serif for large figures and findings, Instrument Sans for everything else (both bundled).
Panels are separated by 10 px gaps and have an 8 px radius, controls use 6 px, borders are 1 px hairlines, and there are no shadows. Chart
titles are one line in sentence case with a one-line subtitle that states what is counted and what is excluded.

**How it fits one screen.** Streamlit has no fixed canvas, so the layout is sized from the viewport: the main
container's chrome (top bar, KPI band, footer, gaps) is fixed and the panel rows share the rest with `vh`-based CSS
heights, and every Plotly chart is told to fill its panel. Streamlit's own header and footer are hidden and the default
padding removed; nothing is clipped or hidden to avoid a scrollbar. On short screens the app drops extras in this
order: the sidebar coverage note (under 790 px of height), then the finding notes and the fourth finding (under 760 px).
On narrow windows (under 1180 px) the KPI sparklines go first.

**Narrower windows and phones.** Below 1180 px wide the one-screen grid gives way to a scrolling layout: panels wrap
two per row (one per row under 640 px), every chart keeps a fixed readable height, and the filter sidebar can be
collapsed and reopened (it starts collapsed on phones).

**Rankings and Unknown.** Bar charts that rank attack, target and weapon types or groups leave the GTD label
*Unknown* out of the ranking and say how many incidents that is in the subtitle. Unknown stays in every total.

## Data

The app reads exactly the 30 columns below and does not depend on the 24 engineered columns that follow them in the CSV.

`eventid, iyear, imonth, iday, country, country_txt, region, region_txt, provstate, city, latitude, longitude,
attacktype1, attacktype1_txt, success, suicide, targtype1, targtype1_txt, targsubtype1_txt, target1, natlty1_txt,
weaptype1, weaptype1_txt, weapsubtype1_txt, gname, individual, claimed, nkill, nwound, property`

Displayed: `eventid`, `iyear`, `imonth`, `country_txt`, `region_txt`, `provstate`, `city`, `latitude`, `longitude`,
`attacktype1_txt`, `targtype1_txt`, `weaptype1_txt`, `gname`, `success`, `suicide`, `nkill`, `nwound`.
Loaded and checked but not displayed: the numeric codes (used to verify one-to-one code/label mapping), `iday`,
`targsubtype1_txt`, `target1`, `natlty1_txt`, `weapsubtype1_txt`, `individual`, `claimed`, `property`.

**Counting rule.** A casualty count is *valid* when it is present, not negative and a whole number (the rule the
notebook's engineered casualty features follow). Missing or invalid counts are never turned into zero. Totals sum
valid counts only and always appear next to the share of incidents that report a count.

### What I found in the files

1. The CSV has 111,855 rows, 54 columns and the years 2000 to 2017, as the notebook says. `eventid` is unique.
   The 54 columns are the 30 analysis columns plus 24 engineered ones.
2. Two incidents in Nigeria (7 July 2012, `eventid` 201207070021 and 201207070022) have `nwound = 8.5`. The
   notebook's engineered columns treat them as unavailable, while its EDA and tests count them. The dashboard
   applies the valid-count rule everywhere: reported injuries are **388,026** (388,043 with the two raw values), and
   Spearman's rho is 0.3581 instead of 0.3582 (n = 103,580 instead of 103,582).
3. "167 countries" is the number of distinct GTD country labels. It includes territories, former states and one
   `International` record, so the KPI is labelled *Countries* with the note "incl. territories (GTD labels)".
4. Casualty data is missing unevenly: injuries are unknown for 22.1% of Sub-Saharan Africa incidents (other regions
   6.9% or less), and for 8.5% to 11% of incidents in 2014 to 2017 against 2% or less in 2009 to 2011. Totals there
   are lower bounds, which is why coverage is shown beside every casualty figure.
5. The last notebook cell compares against `'No Casualties'`, but the label is `'No casualties'`, so it returns 0.

## KPI definitions

| KPI | Definition |
|---|---|
| Incidents | Number of unique `eventid` values in the filtered data |
| Reported fatalities | Sum of valid `nkill` in the filtered data. Shown with the share of incidents that report a count |
| Reported injuries | Same for `nwound` |
| Countries | Distinct `country_txt` labels in the filtered data |
| Success rate | Incidents with `success = 1` divided by incidents with a known 0/1 flag |
| Coordinates available | Share of incidents with valid latitude and longitude (the rest are not drawn on the map) |

## Validation

`python validate.py` recomputes everything independently from the raw CSV and compares:

- data integrity: shape, period, unique IDs, code/label mapping, coordinates, sentinel values, the two fractional counts,
  and agreement with the notebook's engineered casualty columns;
- KPIs for seven selections (all data, a period, a single year, a country, two regions, an attack/target pair, a region
  and period) against separate pandas code;
- chart totals: every chart's data adds back to the filtered data (23 sub-checks per selection);
- filters, empty selections, and all-unknown casualties (reported as unknown, never zero);
- the four statistical tests against the notebook's results, plus a Holm worked example;
- the app itself, headless: every view, a filter, and an empty selection in every view, with no exceptions.

Beyond that, the running app was driven in headless Chromium: filters set through the real widgets produced the same
KPI values as independent pandas, and no page scroll appeared in any view at 1280x720, 1366x768, 1440x900 and
1920x1080. The browser contacted only `localhost`.

## Known limitations

- Built and tested with Streamlit 1.66.1 and Plotly 7.1.0 (pinned). The layout CSS targets Streamlit's internal element
  IDs, so a different Streamlit version may need small CSS changes; the Playwright tests catch that.
- Tested in Chromium only (`tests/e2e`). Safari and Firefox were not tried.
- No-scroll is checked for desktop viewports from 1280x720 to 1920x1080. Below 1180 px wide the page scrolls by design.
  The sidebar can scroll internally on short screens when many filter tags are selected; the main dashboard does not.
- A failing chart is contained: its panel shows "This panel could not be drawn", the error is logged, and the rest of
  the view renders.
- Statistics are exploratory. The chi-square p-value is asymptotic (the notebook used a Monte Carlo test for sparse
  cells). Incidents cluster by country, year and group, so p-values are optimistic.
- GTD `success` is the tactical-success flag, not a mission outcome. Recorded incident counts reflect both events and how
  completely they were documented, which is why the post-2011 rise should be read with care.
- The map aggregates to 0.5 degree cells; bubble area is scaled within the current selection, not across selections.

## Project structure

```
app.py                 Streamlit entry point: layout, filters, navigation, views
core.py                data loading, validity rule, filtering, KPIs, aggregates, statistics (no Streamlit)
charts.py              Plotly figure builders
theme.py               design tokens, CSS, HTML builders
validate.py            independent validation report (60 checks)
data/                  gtd_cleaned.parquet + .meta.json (built from global_cleaned.csv)
scripts/               build_data.py (CSV -> Parquet), screenshots.py
tests/                 pytest suite; tests/e2e holds the Playwright layout tests
static/fonts/          bundled fonts, served by Streamlit static serving
assets/                world outline and favicon (see assets/LICENSES.md)
docs/                  screenshots, validation report, implementation plan
requirements.txt       runtime (pinned); requirements-dev.txt adds pytest, ruff, playwright
pyproject.toml         ruff and pytest configuration
.streamlit/config.toml
.github/workflows/     CI
```

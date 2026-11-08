"""One module per page; each exposes ``render(ctx: ui.Ctx)`` and draws the page body to the right of the filters."""
from views import analysis, data_methods, groups, human_impact, incidents, overview, regions, trends

PAGES = {
    "Overview": overview.render,
    "Incidents": incidents.render,
    "Groups": groups.render,
    "Regions": regions.render,
    "Trends": trends.render,
    "Human Impact": human_impact.render,
    "Analysis": analysis.render,
    "Data & Methods": data_methods.render,
}

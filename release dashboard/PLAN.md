# Home — Release & Patch Command Center

Operational dashboard on the **Home** page (`release dashboard/`). Aggregates Patch Lifecycle data into summary cards, charts, and business insights. Patch Lifecycle remains the system of record for edits.

## Goals

1. Show release/patch health without opening the full tracker.
2. Reuse Patch Lifecycle business rules (FC/WM sides, lifecycle statuses, pending detection).
3. Click-through from cards and insights into Patch Lifecycle with matching filters.
4. Polished Plotly charts with semantic colors (green/yellow/orange/red/blue/teal/purple).

## Architecture

| Module | Role |
|--------|------|
| `release dashboard/ui.py` | Layout, filters, cards, chart grid |
| `release dashboard/dashboard_config.py` | Colors, chart theme, type filter labels |
| `release dashboard/charts.py` | Plotly figure builders |
| `release dashboard/insights.py` | Rule-based “Key insights” sentences |
| `release dashboard/nav.py` | Navigate to Patch Lifecycle with prefilters |
| `patch lifecycle/analytics.py` | Metric computation (no Streamlit) |
| `patch lifecycle/nav_state.py` | Consume prefilters inside Patch Lifecycle |
| `tool_module_loader.load_tool_module()` | Load analytics from patch lifecycle folder |

## Filters (top bar)

| Filter | Options | Scope |
|--------|---------|--------|
| Environment | FC Patches · WM Patches · All Patches | Same as Patch Lifecycle side toggle |
| Date | This Week · This Month · Current Release · Custom Range · All Time | `created_at` on patch row |
| Patch type | All · Weekly · Urgent · Demo UAT · Release | Subset of patch types |

**Current Release:** matches `branch_name` or `release_name` against `CURRENT_RELEASE` env var, else latest hotfix branch in DB.

## Summary cards

**Row 1:** Open · Pending UAT · Pending Stage · Pending Queries · Blocked · Ready To Close  

**Row 2:** Weekly Hotfix · Urgent · Release · Demo UAT · Pending Prod/Master · Closed This Month  

Each card has **View →** opening Patch Lifecycle with relevant prefilters.

## Charts

1. **Release readiness gauges** — release / UAT / stage readiness %
2. **Patch status pie** — Open · In Progress · Blocked · Ready To Close · Closed
3. **FC vs WM donut** — fc / wm / both distribution
4. **Pending action bar** — horizontal bar by lifecycle step (FC or WM fields per side filter)
5. **Patch type bar** — counts by patch type
6. **Weekly trend** — created vs closed per week (last 8 weeks)
7. **Developer workload** — open / blocked / total by developer (top 10)
8. **Aging bar** — open patches by age bucket (0–2, 3–5, 6–10, 10+ days)

## Key insights

Template rules (no LLM), e.g.:

- UAT carry-forward pending count
- Urgent patches still open
- WM stage pending
- FC release branch pending
- Pending DB queries
- Release readiness % and drift risk (High/Medium/Low)
- Ready-to-close count

Each insight can link to Patch Lifecycle.

## Readiness formulas

| Metric | Formula |
|--------|---------|
| Release readiness | `(Closed + Ready To Close) / patches in scope × 100` |
| UAT readiness | patches without pending UAT steps (or closed) / scope × 100 |
| Stage readiness | patches without pending stage steps (or closed) / scope × 100 |

## Click-through / navigation

Home sets `st.session_state["patch_lifecycle_prefilters"]` and switches sidebar view to **Patch Lifecycle**.

Patch Lifecycle `render()` calls `consume_prefilters()` → applies side, view, patch type, developer, pending scope.

## Color semantics

| Color | Meaning |
|-------|---------|
| Green | Completed / healthy |
| Yellow | Pending / attention |
| Orange | Aging / due soon |
| Red | Blocked / urgent / high risk |
| Blue | In progress / informational |
| Teal | FC indicator |
| Purple | WM indicator |

## Exclusions

Patches with manual override **Cancelled**, **Reverted**, or **Duplicate** are excluded from dashboard scope. Archived patches never appear.

## Dependencies

- `plotly>=5.18.0`
- `pandas>=2.0.0`

## Future enhancements

- Chart segment click → drill-down (Streamlit Plotly events)
- `closed_at` from activity log for accurate “closed this month”
- `@st.cache_data` on analytics (60s TTL)
- Config UI for Current Release instead of env var
- DB Query / Configuration type filters on Home

## Tests

`patch lifecycle/tests/test_analytics.py` — metric rules with in-memory or temp DB patterns (reuse repository tests setup).

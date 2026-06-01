"""Streamlit Home — Release & Patch Command Center."""

from __future__ import annotations

from datetime import date

import streamlit as st

import charts
import dashboard_config as dash_config
import insights
import nav

_SIDE_KEY = "rd_side_filter"
_DATE_KEY = "rd_date_preset"
_TYPE_KEY = "rd_patch_type"
_CUSTOM_START = "rd_custom_start"
_CUSTOM_END = "rd_custom_end"

_CARD_PREFILTERS: dict[str, dict] = {
    "total_open": {"view": "Pending follow-ups"},
    "pending_uat": {"view": "Pending follow-ups", "require_pending": True},
    "pending_stage": {"view": "Pending follow-ups", "require_pending": True},
    "pending_queries": {"view": "Pending follow-ups", "require_pending": True},
    "blocked": {"view": "Pending follow-ups"},
    "ready_to_close": {"view": "All patches"},
    "closed_month": {"view": "All patches"},
    "urgent": {"view": "Pending follow-ups", "patch_type": "Urgent Hotfix"},
    "weekly": {"view": "All patches", "patch_type": "Weekly Hotfix"},
    "release": {"view": "All patches", "patch_type": "Release Patch"},
    "demo_uat": {"view": "All patches", "patch_type": "Demo UAT Patch"},
    "pending_production": {"view": "Pending follow-ups", "require_pending": True},
}

_INSIGHT_PREFILTERS: dict[str, dict] = {
    "pending_uat": {"view": "Pending follow-ups", "require_pending": True},
    "urgent": {"view": "Pending follow-ups", "patch_type": "Urgent Hotfix"},
    "pending_stage": {"view": "Pending follow-ups", "require_pending": True},
    "pending_release_branch": {"view": "Pending follow-ups", "require_pending": True},
    "pending_queries": {"view": "Pending follow-ups", "require_pending": True},
    "pending_production": {"view": "Pending follow-ups", "require_pending": True},
    "blocked": {"view": "Pending follow-ups"},
    "ready_to_close": {"view": "All patches"},
}


def _load_pl_module(module_name: str):
    from tool_module_loader import load_tool_module

    return load_tool_module("patch lifecycle", module_name)


def _analytics():
    return _load_pl_module("analytics")


def _inject_dashboard_styles() -> None:
    st.markdown(
        """
        <style>
            .rd-metric-card {
                background: var(--secondary-background-color, #f8f9fb);
                border-radius: 12px;
                padding: 0.85rem 1rem 0.65rem 1rem;
                border: 1px solid rgba(120, 130, 140, 0.18);
                border-left: 4px solid var(--accent, #1565c0);
                min-height: 92px;
                box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }
            .rd-metric-label {
                font-size: 0.82rem;
                color: #546e7a;
                font-weight: 600;
                letter-spacing: 0.02em;
                text-transform: uppercase;
            }
            .rd-metric-value {
                font-size: 1.85rem;
                font-weight: 750;
                line-height: 1.15;
                margin-top: 0.15rem;
                color: #263238;
            }
            .rd-insight {
                border-left: 4px solid var(--accent, #1565c0);
                background: var(--secondary-background-color, #f8f9fb);
                color: #263238;
                padding: 0.65rem 0.85rem;
                border-radius: 8px;
                margin-bottom: 0.45rem;
                font-size: 0.95rem;
            }
            .rd-section-title {
                font-weight: 650;
                font-size: 1.05rem;
                margin: 1.2rem 0 0.5rem 0;
                color: #263238;
            }
            [data-theme="dark"] .rd-metric-card,
            .stApp[data-theme="dark"] .rd-metric-card {
                background: #262730;
                border-color: rgba(255,255,255,0.12);
                box-shadow: 0 1px 3px rgba(0,0,0,0.35);
            }
            [data-theme="dark"] .rd-metric-label,
            .stApp[data-theme="dark"] .rd-metric-label {
                color: #b0b8c4;
            }
            [data-theme="dark"] .rd-metric-value,
            .stApp[data-theme="dark"] .rd-metric-value {
                color: #fafafa;
            }
            [data-theme="dark"] .rd-insight,
            .stApp[data-theme="dark"] .rd-insight {
                background: #262730;
                color: #e8eaed;
                border-color: rgba(255,255,255,0.12);
            }
            [data-theme="dark"] .rd-insight strong,
            .stApp[data-theme="dark"] .rd-insight strong {
                color: #ffffff;
            }
            [data-theme="dark"] .rd-section-title,
            .stApp[data-theme="dark"] .rd-section-title {
                color: #fafafa;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(label: str, value: int | float, accent: str) -> str:
    display = int(value) if float(value).is_integer() else value
    return (
        f'<div class="rd-metric-card" style="--accent:{accent};">'
        f'<div class="rd-metric-label">{label}</div>'
        f'<div class="rd-metric-value">{display}</div>'
        f"</div>"
    )


def _render_card_column(
    col,
    *,
    label: str,
    value: int | float,
    accent: str,
    card_key: str,
    side_filter: str,
) -> None:
    with col:
        st.markdown(_metric_card(label, value, accent), unsafe_allow_html=True)
        pre = dict(_CARD_PREFILTERS.get(card_key, {"view": "All patches"}))
        pre["side_filter"] = side_filter
        if st.button("View →", key=f"rd_card_{card_key}", use_container_width=True):
            nav.go_to_patch_lifecycle(**pre)


def _filters(analytics_mod):
    pl_config = _load_pl_module("config")
    c1, c2, c3 = st.columns([1.2, 1.2, 1.2])
    with c1:
        side = st.radio(
            "Environment",
            options=list(pl_config.SIDE_FILTERS),
            horizontal=True,
            key=_SIDE_KEY,
            label_visibility="collapsed",
        )
    with c2:
        date_preset = st.selectbox(
            "Date range",
            options=list(analytics_mod.DATE_PRESETS),
            index=list(analytics_mod.DATE_PRESETS).index(analytics_mod.DATE_ALL),
            key=_DATE_KEY,
        )
    with c3:
        type_labels = [label for label, _ in dash_config.TYPE_FILTER_OPTIONS]
        type_map = {label: val for label, val in dash_config.TYPE_FILTER_OPTIONS}
        type_label = st.selectbox("Patch type", options=type_labels, key=_TYPE_KEY)
        patch_type = type_map[type_label]

    custom_start = custom_end = None
    if date_preset == analytics_mod.DATE_CUSTOM:
        d1, d2 = st.columns(2)
        with d1:
            custom_start = st.date_input("From", value=date.today().replace(day=1), key=_CUSTOM_START)
        with d2:
            custom_end = st.date_input("To", value=date.today(), key=_CUSTOM_END)

    return analytics_mod.DashboardFilters(
        side_filter=side,
        date_preset=date_preset,
        patch_type=patch_type,
        custom_start=custom_start,
        custom_end=custom_end,
    )


def render() -> None:
    analytics_mod = _analytics()
    _inject_dashboard_styles()

    st.title(dash_config.PAGE_TITLE)
    st.caption(dash_config.PAGE_SUBTITLE)

    filters = _filters(analytics_mod)
    metrics = analytics_mod.compute_dashboard_metrics(filters)

    st.markdown('<div class="rd-section-title">Release readiness</div>', unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    with g1:
        st.plotly_chart(
            charts.readiness_gauge("Release Readiness", metrics.release_readiness_pct),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with g2:
        st.plotly_chart(
            charts.readiness_gauge("UAT Readiness", metrics.uat_readiness_pct, bar_color=dash_config.COLOR_ORANGE),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with g3:
        st.plotly_chart(
            charts.readiness_gauge("Stage Readiness", metrics.stage_readiness_pct, bar_color=dash_config.COLOR_YELLOW),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.markdown('<div class="rd-section-title">At a glance</div>', unsafe_allow_html=True)
    row1 = st.columns(6)
    cards_r1 = [
        ("Open Patches", metrics.total_open, dash_config.CARD_ACCENTS["open"], "total_open"),
        ("Pending UAT", metrics.pending_uat, dash_config.CARD_ACCENTS["uat"], "pending_uat"),
        ("Pending Stage", metrics.pending_stage, dash_config.CARD_ACCENTS["stage"], "pending_stage"),
        ("Pending Queries", metrics.pending_queries, dash_config.CARD_ACCENTS["queries"], "pending_queries"),
        ("Blocked", metrics.blocked, dash_config.CARD_ACCENTS["blocked"], "blocked"),
        ("Ready To Close", metrics.ready_to_close, dash_config.CARD_ACCENTS["ready"], "ready_to_close"),
    ]
    for col, (label, val, accent, key) in zip(row1, cards_r1):
        _render_card_column(
            col, label=label, value=val, accent=accent, card_key=key, side_filter=filters.side_filter
        )

    row2 = st.columns(6)
    cards_r2 = [
        ("Weekly Hotfix", metrics.weekly_hotfix, dash_config.COLOR_BLUE, "weekly"),
        ("Urgent", metrics.urgent, dash_config.CARD_ACCENTS["urgent"], "urgent"),
        ("Release", metrics.release, dash_config.COLOR_TEAL, "release"),
        ("Demo UAT", metrics.demo_uat, dash_config.COLOR_PURPLE, "demo_uat"),
        ("Pending Prod / Master", metrics.pending_production_master, dash_config.COLOR_ORANGE, "pending_production"),
        ("Closed This Month", metrics.closed_this_month, dash_config.CARD_ACCENTS["closed"], "closed_month"),
    ]
    for col, (label, val, accent, key) in zip(row2, cards_r2):
        _render_card_column(
            col, label=label, value=val, accent=accent, card_key=key, side_filter=filters.side_filter
        )

    c_left, c_right = st.columns(2)
    with c_left:
        st.plotly_chart(
            charts.status_pie_chart(metrics.status_pie),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with c_right:
        st.plotly_chart(
            charts.side_donut_chart(metrics.side_distribution),
            use_container_width=True,
            config={"displayModeBar": False},
        )
        wm_cols = st.columns(2)
        with wm_cols[0]:
            if st.button("Open WM patches →", key="rd_go_wm", use_container_width=True):
                nav.go_to_patch_lifecycle(side_filter="WM Patches", view="All patches")
        with wm_cols[1]:
            if st.button("Open FC patches →", key="rd_go_fc", use_container_width=True):
                nav.go_to_patch_lifecycle(side_filter="FC Patches", view="All patches")

    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(
            charts.pending_action_bar(metrics.pending_actions),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with c4:
        st.plotly_chart(
            charts.patch_type_bar(metrics.patch_type_counts),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(
            charts.weekly_trend_chart(metrics.weekly_created, metrics.weekly_closed),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with c6:
        st.plotly_chart(
            charts.developer_workload_chart(
                metrics.developer_total,
                metrics.developer_open,
                metrics.developer_blocked,
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )

    st.plotly_chart(
        charts.aging_chart(metrics.aging_buckets),
        use_container_width=True,
        config={"displayModeBar": False},
    )

    st.markdown('<div class="rd-section-title">Key insights</div>', unsafe_allow_html=True)
    for idx, item in enumerate(insights.build_insights(metrics, side_filter=filters.side_filter)):
        color = insights.insight_border_color(item.tone)
        st.markdown(
            f'<div class="rd-insight" style="--accent:{color};">{item.message}</div>',
            unsafe_allow_html=True,
        )
        if item.prefilter_key:
            pre = dict(_INSIGHT_PREFILTERS.get(item.prefilter_key, {"view": "Pending follow-ups"}))
            pre["side_filter"] = filters.side_filter
            if st.button("View in Patch Lifecycle →", key=f"rd_insight_{idx}_{item.prefilter_key}"):
                nav.go_to_patch_lifecycle(**pre)

    with st.expander("Release tools & project info", expanded=False):
        st.markdown(
            "Use the sidebar **Release Overview/Tools** to open Patch Lifecycle, "
            "Hotfix Branch Automation, or SRE Generator."
        )
        if st.button("Open Patch Lifecycle", type="primary", key="rd_open_pl"):
            nav.go_to_patch_lifecycle(view="All patches", side_filter=filters.side_filter)

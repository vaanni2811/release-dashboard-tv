"""Cross-page navigation state for Patch Lifecycle deep links."""

from __future__ import annotations

from typing import Any

import streamlit as st

PREFILTER_SESSION_KEY = "patch_lifecycle_prefilters"


def set_prefilters(**kwargs: Any) -> None:
    st.session_state[PREFILTER_SESSION_KEY] = dict(kwargs)


def consume_prefilters() -> dict[str, Any]:
    """Return and clear one-shot prefilters set by Home or app navigation."""
    raw = st.session_state.pop(PREFILTER_SESSION_KEY, None)
    return dict(raw) if raw else {}


def apply_prefilters(pref: dict[str, Any]) -> None:
    """Apply navigation prefilters to Patch Lifecycle session keys."""
    import config

    if pref.get("side_filter") in config.SIDE_FILTERS:
        st.session_state[config.SIDE_FILTER_SESSION_KEY] = pref["side_filter"]

    view = pref.get("view")
    if view in ("All patches", "Pending follow-ups", "Create patch", "Patch detail"):
        st.session_state["pl_view"] = view

    if pref.get("patch_type"):
        st.session_state["_pl_prefilter_type"] = pref["patch_type"]
    if pref.get("require_pending"):
        st.session_state["_pl_prefilter_pending"] = True
    if pref.get("developer"):
        st.session_state["_pl_prefilter_developer"] = pref["developer"]

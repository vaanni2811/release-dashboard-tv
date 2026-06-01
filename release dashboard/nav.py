"""Navigate from Home dashboard into Patch Lifecycle with filters."""

from __future__ import annotations

from typing import Any

import streamlit as st

PREFILTER_KEY = "patch_lifecycle_prefilters"
TOOL_NAME = "Patch Lifecycle"


def go_to_patch_lifecycle(**prefilters: Any) -> None:
    st.session_state[PREFILTER_KEY] = dict(prefilters)
    st.session_state.selected_view = TOOL_NAME
    st.rerun()

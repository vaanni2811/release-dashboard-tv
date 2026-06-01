"""Streamlit UI for the release dashboard (home)."""

from __future__ import annotations

import streamlit as st

TOOLS: tuple[tuple[str, str, str], ...] = (
    (
        "HP Branch Cut",
        "hotfix branch automation",
        "Create hotfix branches in Bitbucket from repo + week; preview naming and lineage.",
    ),
    (
        "SRE Generator",
        "SRE generator",
        "Build ready-to-paste SRE/Jira tickets (weekly, urgent, UAT) from patch metadata.",
    ),
)


def render() -> None:
    st.title("Release dashboard")
    st.markdown(
        "Local Streamlit workspace for FranConnect release workflows. "
        "Pick a tool in the sidebar."
    )

    st.subheader("Tools in this project")
    for name, folder, description in TOOLS:
        with st.expander(name, expanded=True):
            st.markdown(description)
            st.caption(f"Folder: `{folder}/`")

    st.subheader("Project layout")
    st.markdown(
        """
| Path | Purpose |
| --- | --- |
| `app.py` | Main entry — sidebar routes to home and tools |
| `tool_loader.py` | Loads each tool's `ui.py` |
| `hotfix branch automation/` | HP Branch Cut (Bitbucket API) |
| `SRE generator/` | SRE ticket generator (no API) |
| `release dashboard/` | This home view |
| `requirements.txt` | Python dependencies |
| `.env.example` | Copy to `.env` for Bitbucket credentials (hotfix only) |
"""
    )

    st.info(
        "**Hotfix tool:** set `BITBUCKET_EMAIL`, `BITBUCKET_API_TOKEN`, and "
        "`BITBUCKET_WORKSPACE` in a local `.env` file (never commit it). "
        "**SRE Generator** does not need credentials."
    )

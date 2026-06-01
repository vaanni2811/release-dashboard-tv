"""Streamlit UI for the release dashboard (home)."""

from __future__ import annotations

import streamlit as st

TOOLS: tuple[tuple[str, str, str], ...] = (
    (
        "Patch Lifecycle",
        "patch lifecycle",
        "Track every patch from capture through production, branch updates, queries, UAT, and closure.",
    ),
    (
        "Hotfix Branch Automation",
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
        "Open **Release Overview/Tools** in the sidebar to pick a tool."
    )

    st.subheader("Release Overview / Tools")
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
| `patch lifecycle/` | Patch registry and lifecycle tracker (planned) |
| `hotfix branch automation/` | Hotfix Branch Automation (Bitbucket API) |
| `SRE generator/` | SRE ticket generator (no API) |
| `release dashboard/` | This home view |
| `requirements.txt` | Python dependencies |
| `.env.example` | Copy to `.env` for Bitbucket credentials (hotfix only) |
"""
    )

    st.info(
        "**Hotfix Branch Automation:** set `BITBUCKET_EMAIL`, `BITBUCKET_API_TOKEN`, and "
        "`BITBUCKET_WORKSPACE` in a local `.env` file (never commit it). "
        "**SRE Generator** and **Patch Lifecycle** (MVP) do not need Bitbucket for basic use."
    )

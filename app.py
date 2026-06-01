"""
Release dashboard — sidebar routes to home and individual tools.

Run: streamlit run app.py
Credentials: copy .env.example to .env at repo root (shared across tools).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore[assignment,misc]

ROOT = Path(__file__).resolve().parent

if load_dotenv:
    load_dotenv(ROOT / ".env", override=False)

import streamlit as st

from tool_loader import load_tool_render

TOOLS: dict[str, str] = {
    "Patch Lifecycle": "patch lifecycle",
    "Hotfix Branch Automation": "hotfix branch automation",
    "SRE Generator": "SRE generator",
}

HOME = "Home"
HOME_DIR = "release dashboard"
TOOLS_SECTION_LABEL = "Release Overview/Tools"


def _view_dirs() -> list[str]:
    return [HOME_DIR, *TOOLS.values()]


def _build_stamp() -> str:
    """Visible build stamp from latest mtime under tool folders and this app."""
    paths = [ROOT / "app.py", ROOT / "tool_loader.py"]
    for tool_dir in _view_dirs():
        tool_path = ROOT / tool_dir
        if tool_path.is_dir():
            paths.extend(p for p in tool_path.rglob("*.py") if p.is_file())
    latest = max(p.stat().st_mtime for p in paths if p.exists())
    return datetime.fromtimestamp(latest).strftime("%Y-%m-%d %H:%M:%S")


def _inject_typography_styles() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                font-size: 16.5px;
            }
            h1 {
                font-size: 2.15rem !important;
                font-weight: 700 !important;
            }
            h2, h3 {
                font-size: 1.35rem !important;
                font-weight: 650 !important;
            }
            section[data-testid="stSidebar"] * {
                font-size: 1.02rem !important;
            }
            section[data-testid="stSidebar"] label {
                font-weight: 650 !important;
            }
            section[data-testid="stSidebar"] .sidebar-tools-label {
                font-weight: 650 !important;
                margin-bottom: 0.35rem;
            }
            section[data-testid="stSidebar"] button[kind="secondary"] {
                font-weight: 550 !important;
                text-align: left;
                justify-content: flex-start;
            }
            section[data-testid="stSidebar"] button[kind="primary"] {
                font-weight: 650 !important;
                text-align: left;
                justify-content: flex-start;
            }
            [data-theme="dark"] .stCaption,
            .stApp[data-theme="dark"] .stCaption,
            [data-theme="dark"] [data-testid="stCaptionContainer"],
            .stApp[data-theme="dark"] [data-testid="stCaptionContainer"] {
                color: #b0b8c4;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Release dashboard",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    _inject_typography_styles()

    if "selected_view" not in st.session_state:
        st.session_state.selected_view = HOME
    # Legacy sidebar label from before rename
    if st.session_state.selected_view == "HP Branch Cut":
        st.session_state.selected_view = "Hotfix Branch Automation"

    with st.sidebar:
        home_selected = st.session_state.selected_view == HOME
        if st.button(
            HOME,
            key="sidebar_home",
            use_container_width=True,
            type="primary" if home_selected else "secondary",
        ):
            st.session_state.selected_view = HOME
            st.rerun()

        st.markdown(
            f'<p class="sidebar-tools-label">{TOOLS_SECTION_LABEL}</p>',
            unsafe_allow_html=True,
        )
        for tool_name in TOOLS:
            is_selected = st.session_state.selected_view == tool_name
            if st.button(
                tool_name,
                key=f"sidebar_tool_{tool_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_view = tool_name
                st.rerun()

    selected_view = st.session_state.selected_view

    st.caption(
        f"Build stamp: `{_build_stamp()}` "
        "(if this does not change after edits, restart `streamlit run app.py`)."
    )

    if selected_view == HOME:
        render = load_tool_render(HOME_DIR)
        render()
    else:
        tool_dir = TOOLS[selected_view]
        render = load_tool_render(tool_dir)
        render()


if __name__ == "__main__":
    main()

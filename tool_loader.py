"""Load Streamlit tool UIs from sibling folders (names may contain spaces)."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

from tool_module_loader import ROOT, load_tool_module, prepare_tool_modules

# Re-export for callers that import from tool_loader.
__all__ = ["load_tool_render", "load_tool_module", "ROOT"]


def load_tool_render(tool_dir: str) -> Callable[[], None]:
    """Import ``ui.render`` from ``ROOT / tool_dir / ui.py``."""
    tool_path = ROOT / tool_dir
    ui_path = tool_path / "ui.py"
    if not ui_path.is_file():
        raise FileNotFoundError(f"Tool UI not found: {ui_path}")

    module_name = f"tool_{tool_dir.replace(' ', '_')}_ui"
    spec = importlib.util.spec_from_file_location(module_name, ui_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load tool module from {ui_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    tool_root = str(tool_path)
    inserted = tool_root not in sys.path
    if inserted:
        sys.path.insert(0, tool_root)
    prepare_tool_modules(tool_path)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(tool_root)

    render = getattr(module, "render", None)
    if not callable(render):
        raise AttributeError(f"{ui_path} must define a render() function")
    return render

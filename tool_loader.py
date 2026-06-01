"""Load Streamlit tool UIs from sibling folders (names may contain spaces)."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Module basenames shared across tools (same filename in each tool folder).
_TOOL_SIBLING_MODULES = frozenset(
    {"logic", "config", "utils", "bitbucket", "bitbucket_auth"},
)


def _evict_foreign_tool_modules(tool_path: Path) -> None:
    """Drop cached sibling imports from other tool folders (e.g. logic, config)."""
    tool_resolved = tool_path.resolve()
    for name in _TOOL_SIBLING_MODULES:
        mod = sys.modules.get(name)
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None)
        if not mod_file:
            continue
        if Path(mod_file).resolve().parent != tool_resolved:
            del sys.modules[name]


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
    tool_root = str(tool_path)
    inserted = tool_root not in sys.path
    if inserted:
        sys.path.insert(0, tool_root)
    _evict_foreign_tool_modules(tool_path)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(tool_root)

    render = getattr(module, "render", None)
    if not callable(render):
        raise AttributeError(f"{ui_path} must define a render() function")
    return render

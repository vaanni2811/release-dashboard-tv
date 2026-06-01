"""Load Streamlit tool UIs from sibling folders (names may contain spaces)."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Module basenames shared across tools (same filename in each tool folder).
# Reload order matters: config first, then dependents (db, display, repository).
_TOOL_SIBLING_MODULES: tuple[str, ...] = (
    "config",
    "logic",
    "utils",
    "bitbucket",
    "bitbucket_auth",
    "db",
    "display",
    "repository",
)


def _module_tool_dir(mod: object) -> Path | None:
    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        return None
    return Path(mod_file).resolve().parent


def _prepare_tool_modules(tool_path: Path) -> None:
    """Drop sibling imports from other tools; reload this tool's cached modules."""
    tool_resolved = tool_path.resolve()

    # Drop cached tool UI modules so each navigation re-binds fresh imports.
    for key in list(sys.modules):
        if key.startswith("tool_") and key.endswith("_ui"):
            del sys.modules[key]

    for name in _TOOL_SIBLING_MODULES:
        mod = sys.modules.get(name)
        if mod is None:
            continue
        mod_dir = _module_tool_dir(mod)
        if mod_dir is None:
            continue
        if mod_dir != tool_resolved:
            del sys.modules[name]
        else:
            importlib.reload(mod)


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
    _prepare_tool_modules(tool_path)
    try:
        spec.loader.exec_module(module)
    finally:
        if inserted:
            sys.path.remove(tool_root)

    render = getattr(module, "render", None)
    if not callable(render):
        raise AttributeError(f"{ui_path} must define a render() function")
    return render

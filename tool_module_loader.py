"""Load Python modules from tool folders (no UI imports — safe from any tool)."""

from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Module basenames shared across tools (same filename in each tool folder).
_TOOL_SIBLING_MODULES: tuple[str, ...] = (
    "config",
    "logic",
    "utils",
    "bitbucket",
    "bitbucket_auth",
    "db",
    "display",
    "repository",
    "analytics",
    "nav_state",
)


def _module_tool_dir(mod: object) -> Path | None:
    mod_file = getattr(mod, "__file__", None)
    if not mod_file:
        return None
    return Path(mod_file).resolve().parent


def prepare_tool_modules(tool_path: Path) -> None:
    """Drop sibling imports from other tools; reload this tool's cached modules."""
    tool_resolved = tool_path.resolve()

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


def load_tool_module(tool_dir: str, module_name: str):
    """Import a submodule from a tool folder (e.g. patch lifecycle analytics)."""
    tool_path = ROOT / tool_dir
    module_path = tool_path / f"{module_name}.py"
    if not module_path.is_file():
        raise FileNotFoundError(f"Tool module not found: {module_path}")

    qual_name = f"tool_{tool_dir.replace(' ', '_')}_{module_name}"
    spec = importlib.util.spec_from_file_location(qual_name, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {module_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[qual_name] = module
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
    return module

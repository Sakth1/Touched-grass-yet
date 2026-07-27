"""Snapshot the installed flet's public API surface to JSON.

Usage:
    python scripts/save-flet-snapshot.py [--output api-snapshot.json]
"""

import argparse
import importlib
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_DEFAULT = _REPO / "api-snapshot.json"


def _category(obj: object) -> str:
    t = type(obj)
    if t.__module__.startswith("flet") and isinstance(obj, type):
        if hasattr(obj, "__dataclass_fields__"):
            return "dataclass"
        if issubclass(obj, type) and hasattr(obj, "__members__"):
            return "enum"
        return "class"
    if callable(obj):
        return "function"
    if isinstance(obj, type(sys)):
        return "module"
    return "other"


def snapshot() -> dict:
    import flet as ft

    names: dict[str, dict] = {}
    for name in sorted(ft.__all__):
        try:
            obj = getattr(ft, name)
        except Exception:
            names[name] = {"error": "cannot resolve"}
            continue

        entry: dict = {"type": _category(obj)}

        if isinstance(obj, type) and hasattr(obj, "__members__"):
            entry["members"] = sorted(obj.__members__)

        if isinstance(obj, type):
            try:
                sig = obj.__init__ if isinstance(obj, type) else obj
                import inspect

                params = list(inspect.signature(sig).parameters)
                entry["params"] = [p for p in params if p != "self" and not p.startswith("_")]
            except Exception:
                pass

        if hasattr(obj, "__module__"):
            entry["module"] = obj.__module__ if isinstance(obj, type) else type(obj).__module__

        names[name] = entry

    return {"flet_version": ft.__version__, "names": names}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(_DEFAULT), help="Path to JSON snapshot file")
    args = parser.parse_args()
    data = snapshot()
    out = Path(args.output)
    out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"Snapshot written to {out}  ({len(data['names'])} names)")


if __name__ == "__main__":
    main()

"""Import sweep: every module under ``src/`` must import and reload cleanly.

Runs in a fresh subprocess so import-time side effects (loggers, registry
reads, ``@ft.control`` decorators) never pollute the test session and are
caught exactly as they would happen at app startup.

A failed import is only acceptable when its traceback passes through a
platform-specific API guard (``ctypes.windll`` / ``pywinauto`` / ``jnius``)
— i.e. the module needs an OS/device API this machine does not provide.
Any other failure, and any warning emitted during import, fails the suite.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from sweep_helpers import PLATFORM_MARKERS, SRC_DIR, discover_module_names

_IMPORT_SCRIPT = r"""
import importlib
import json
import sys
import traceback
import warnings

results = {}
for name in json.loads(sys.argv[1]):
    entry = {"warnings": [], "error": None, "traceback": None}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            importlib.import_module(name)
            importlib.reload(importlib.import_module(name))
        except BaseException as exc:
            entry["error"] = f"{type(exc).__name__}: {exc}"
            entry["traceback"] = traceback.format_exc()
    entry["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught]
    results[name] = entry
print(json.dumps(results))
"""


def test_every_module_imports_and_reloads_cleanly(chdir_tmp):
    modules = discover_module_names()
    assert modules, "module discovery found nothing under src/"

    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    proc = subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT, json.dumps(modules)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert proc.returncode == 0, f"import subprocess crashed:\n{proc.stderr}"

    results = json.loads(proc.stdout)
    assert set(results) == set(modules), "import sweep did not cover every module"

    failures: list[str] = []
    platform_gaps: list[str] = []
    for name, entry in sorted(results.items()):
        if entry["error"]:
            target = platform_gaps if _is_platform_gap(entry["traceback"]) else failures
            target.append(f"{name}:\n{entry['traceback']}")
        for warning in entry["warnings"]:
            failures.append(f"{name}: import emitted warning: {warning}")

    if platform_gaps:
        pytest.fail(
            "Modules skipped as platform-unavailable (NOT expected on this machine):\n"
            + "\n".join(platform_gaps)
        )

    if failures:
        pytest.fail("Import sweep found problems:\n\n" + "\n\n".join(failures))


def _is_platform_gap(traceback_text: str | None) -> bool:
    if not traceback_text:
        return False
    return any(marker in traceback_text for marker in PLATFORM_MARKERS)

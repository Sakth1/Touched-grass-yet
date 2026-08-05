"""Replicate the cloud CI lint+test jobs in a pristine local copy.

Recreates the ``actions/checkout`` + ``uv sync --frozen`` + test scenario
from ``.github/workflows/ci.yml``:

1. Copies the working tree into a fresh temp dir using git's own file list
   (tracked + untracked non-ignored) — no ``__pycache__``, no ``.pytest_cache``,
   no ``.venv``, exactly like a fresh checkout.
2. Runs ``uv sync --frozen`` there, producing a brand-new venv whose
   site-packages has no pre-compiled ``.pyc`` files.
3. Runs the same commands as the CI ``lint`` and ``test`` jobs:
   ``ruff check``, ``pyright``, ``pytest``.

Because every module compiles from source on first import, environment-only
failures (e.g. compile-time ``SyntaxWarning`` emitted by lazy imports) that
local ``.pyc`` caches mask are reproduced exactly as on the CI runner.

Usage (from the repo root):

    uv run python scripts/ci/local_ci.py [--keep]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]

_STEPS = (
    ("ruff check", ["uv", "run", "ruff", "check", "src/", "tests/"]),
    ("pyright", ["uv", "run", "pyright", "src/"]),
    (
        "pytest",
        ["uv", "run", "pytest", "tests/", "-v", "--tb=short", "-q"],
    ),
)


def _git_files() -> list[str]:
    """Every file a fresh checkout would contain (tracked + untracked)."""
    tracked = subprocess.check_output(
        ["git", "ls-files", "-z"], cwd=_REPO_ROOT, text=True
    ).split("\0")
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=_REPO_ROOT,
        text=True,
    ).split("\0")
    return [f for f in [*tracked, *untracked] if f]


def _copy_tree(dest: Path) -> None:
    for rel in _git_files():
        src = _REPO_ROOT / rel
        if not src.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)


def _run(cmd: list[str], cwd: Path) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the temp copy on failure for inspection",
    )
    args = parser.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="unscreen-ci-"))
    try:
        print(f"=== Fresh checkout copy: {tmp} ===")
        _copy_tree(tmp)
        print("=== uv sync --frozen ===")
        _run(["uv", "sync", "--frozen"], cwd=tmp)
        for name, cmd in _STEPS:
            print(f"=== {name} ===")
            _run(cmd, cwd=tmp)
        print("=== Cloud CI replication passed ===")
        return 0
    except subprocess.CalledProcessError as exc:
        print(
            f"=== Cloud CI replication FAILED (exit {exc.returncode}) ===",
            file=sys.stderr,
        )
        if args.keep:
            print(f"Temp copy kept at: {tmp}", file=sys.stderr)
        return exc.returncode
    finally:
        if not args.keep:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

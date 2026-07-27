"""Compare current flet API against a saved snapshot.

Exits with code 0 if compatible, 1 if breaking changes found.

Usage:
    python scripts/check_flet_snapshot.py [--snapshot api-snapshot.json]
"""

import argparse
import json
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO / "scripts"))
_DEFAULT = _REPO / "api-snapshot.json"


def _load_snapshot(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(snapshot_path: Path) -> int:
    from save_flet_snapshot import snapshot as current_snapshot

    old = _load_snapshot(snapshot_path)
    cur = current_snapshot()

    old_names = set(old.get("names", {}))
    cur_names = set(cur.get("names", {}))

    issues: list[str] = []
    old_ver = old.get("flet_version", "?")
    cur_ver = cur.get("flet_version", "?")

    # Removed names
    removed = old_names - cur_names
    for name in sorted(removed):
        issues.append(f"  - {name}  (present in {old_ver}, missing in {cur_ver})")

    # Added names (informational, not an error)
    added = cur_names - old_names
    for name in sorted(added):
        issues.append(f"  + {name}  (new in {cur_ver})")

    # Changed params
    for name in sorted(old_names & cur_names):
        old_entry = old["names"][name]
        cur_entry = cur["names"][name]
        old_params = set(old_entry.get("params", []))
        cur_params = set(cur_entry.get("params", []))
        removed_params = old_params - cur_params
        if removed_params:
            issues.append(f"  ~ {name} lost params: {sorted(removed_params)}")
        added_params = cur_params - old_params
        if added_params:
            issues.append(f"  ~ {name} gained params: {sorted(added_params)}")

        old_members = set(old_entry.get("members", []))
        cur_members = set(cur_entry.get("members", []))
        removed_members = old_members - cur_members
        if removed_members:
            issues.append(f"  ~ {name} lost enum members: {sorted(removed_members)}")

    if issues:
        print(f"Flet API snapshot mismatch  ({old_ver} -> {cur_ver}):")
        for line in issues:
            print(line)
        return 1

    print(f"Flet API snapshot compatible  ({old_ver} -> {cur_ver})")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", default=str(_DEFAULT), help="Path to JSON snapshot file")
    args = parser.parse_args()
    snap_path = Path(args.snapshot)
    if not snap_path.exists():
        print(f"No snapshot found at {snap_path}. Run scripts/save-flet-snapshot.py first.")
        sys.exit(0)
    sys.exit(compare(snap_path))


if __name__ == "__main__":
    main()

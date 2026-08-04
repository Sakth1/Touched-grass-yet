import json
import os
from pathlib import Path

from browser_url_extractor.utils import is_trackable_url

try:
    import lz4.block
except ImportError:
    lz4_block = None


def decompress_mozlz4(path: str | os.PathLike) -> bytes | None:
    raw = Path(path).read_bytes()
    if raw[:8] != b"mozLz40\0":
        return None
    try:
        return lz4.block.decompress(raw[8:])
    except Exception:
        return None


def parse_recovery(data: bytes) -> list[dict]:
    try:
        session = json.loads(data)
    except json.JSONDecodeError:
        return []

    tabs_info: list[dict] = []
    windows = session.get("windows", [])
    active_win_index = session.get("selectedWindow", 0)

    for win_index, win in enumerate(windows):
        sel_tab_index = win.get("selected", 1) - 1
        tabs = win.get("tabs", [])
        for tab_index, tab in enumerate(tabs):
            entries = tab.get("entries", [])
            entry_index = tab.get("index", 1) - 1
            if 0 <= entry_index < len(entries):
                entry = entries[entry_index]
                tabs_info.append(
                    {
                        "window_index": win_index,
                        "tab_index": tab_index,
                        "is_active_window": win_index == active_win_index,
                        "is_selected_tab": tab_index == sel_tab_index,
                        "url": entry.get("url"),
                        "title": entry.get("title"),
                    }
                )

    active = [t for t in tabs_info if t["is_active_window"] and t["is_selected_tab"]]
    if active:
        return active

    active_win = [t for t in tabs_info if t["is_active_window"]]
    if active_win:
        return active_win

    return tabs_info


def get_recovery_path(backups_dir: str) -> str | None:
    candidates = [
        "recovery.jsonlz4",
        "recovery.baklz4",
        "previous.jsonlz4",
    ]
    for name in candidates:
        p = os.path.join(backups_dir, name)
        if os.path.isfile(p):
            return p
    return None


def get_active_tab_url(backups_dir: str) -> str | None:
    if lz4_block is None:
        return None

    rpath = get_recovery_path(backups_dir)
    if not rpath:
        return None

    decompressed = decompress_mozlz4(rpath)
    if decompressed is None:
        return None

    tabs = parse_recovery(decompressed)
    for t in tabs:
        if t["is_active_window"] and t["is_selected_tab"]:
            url = t["url"]
            if is_trackable_url(url):
                return url

    if tabs:
        url = tabs[0]["url"]
        if is_trackable_url(url):
            return url

    return None

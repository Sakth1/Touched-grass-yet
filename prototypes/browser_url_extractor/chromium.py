import os
import struct
import time
from pathlib import Path

from browser_url_extractor.utils import is_trackable_url

SNSS_MAGIC = b"SNSS"
CMD_TAB_WINDOW = 0
CMD_UPDATE_NAV = 6
CMD_SEL_NAV_INDEX = 7
CMD_SEL_TAB = 8
CMD_SET_ACTIVE_WINDOW = 20


def _align4(pos: int) -> int:
    return (pos + 3) & ~3


def _read_string(data: bytes, pos: int) -> tuple[str | None, int]:
    if pos + 4 > len(data):
        return None, pos
    length = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    if length == 0 or length > 500000 or pos + length > len(data):
        return None, pos
    try:
        s = data[pos : pos + length].decode("utf-8", errors="replace")
    except Exception:
        s = None
    pos = _align4(pos + length)
    return s, pos


def _read_string16(data: bytes, pos: int) -> tuple[str | None, int]:
    if pos + 4 > len(data):
        return None, pos
    length = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    if length == 0 or length > 250000 or pos + length * 2 > len(data):
        return None, pos
    try:
        s = data[pos : pos + length * 2].decode("utf-16-le", errors="replace")
    except Exception:
        s = None
    pos = _align4(pos + length * 2)
    return s, pos


def parse_session_file(path: str | os.PathLike) -> list[dict]:
    data = Path(path).read_bytes()
    if len(data) < 8 or data[:4] != SNSS_MAGIC:
        return []

    version = struct.unpack_from("<I", data, 4)[0]
    if version not in (1, 3):
        return []

    pos = 8
    tabs: dict[int, dict] = {}
    windows: dict[int, list[int]] = {}
    selected_tabs: dict[int, int] = {}
    active_window_id: int | None = None

    while pos + 3 <= len(data):
        cmd_size = struct.unpack_from("<h", data, pos)[0]
        if cmd_size <= 0:
            pos += 2
            continue
        cmd_id = data[pos + 2]
        payload = data[pos + 3 : pos + cmd_size + 2]
        pos += cmd_size + 2

        if cmd_id == CMD_TAB_WINDOW and len(payload) >= 8:
            tab_id = struct.unpack_from("<i", payload, 0)[0]
            window_id = struct.unpack_from("<i", payload, 4)[0]
            windows.setdefault(window_id, []).append(tab_id)

        elif cmd_id == CMD_UPDATE_NAV and len(payload) >= 20:
            p = 4
            tab_id = struct.unpack_from("<i", payload, p)[0]
            p += 4
            nav_index = struct.unpack_from("<i", payload, p)[0]
            p += 4
            url, p = _read_string(payload, p)
            title, _p = _read_string16(payload, p)
            if url is None:
                continue
            tabs[tab_id] = {"url": url, "title": title, "nav_index": nav_index}

        elif cmd_id == CMD_SEL_TAB and len(payload) >= 8:
            window_id = struct.unpack_from("<i", payload, 0)[0]
            tab_index = struct.unpack_from("<i", payload, 4)[0]
            selected_tabs[window_id] = tab_index

        elif cmd_id == CMD_SET_ACTIVE_WINDOW and len(payload) >= 4:
            active_window_id = struct.unpack_from("<i", payload, 0)[0]

    result = []
    for win_id, tab_ids in windows.items():
        sel_index = selected_tabs.get(win_id, 0)
        if sel_index < len(tab_ids):
            tab_id = tab_ids[sel_index]
            info = tabs.get(tab_id)
            if info:
                is_active = win_id == active_window_id
                result.append(
                    {
                        "window_id": win_id,
                        "tab_id": tab_id,
                        "url": info["url"],
                        "title": info["title"],
                        "nav_index": info["nav_index"],
                        "is_active_window": is_active,
                    }
                )
    return result


def _is_recent(path: Path, max_age_s: float = 180) -> bool:
    try:
        return time.time() - path.stat().st_mtime < max_age_s
    except OSError:
        return False


def get_active_tab_url(
    browser_name: str, session_dir: str, max_stale_s: float = 300
) -> str | None:
    sess_path = Path(session_dir)
    session_files = sorted(
        sess_path.glob("Session_*"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    if not session_files:
        return None

    tabs_info = []
    for sf in session_files:
        if sf.stat().st_size == 0:
            continue
        if not _is_recent(sf, max_stale_s):
            continue
        try:
            entries = parse_session_file(str(sf))
            tabs_info.extend(entries)
        except Exception:
            continue
        if tabs_info:
            break

    active_tabs = [t for t in tabs_info if t["is_active_window"]]
    if active_tabs:
        active_tabs.sort(key=lambda t: t["window_id"])
        url = active_tabs[0]["url"]
        return url if is_trackable_url(url) else None

    fallback = _try_tabs_file(session_dir, max_stale_s)
    if fallback:
        return fallback

    if tabs_info:
        url = tabs_info[0]["url"]
        return url if is_trackable_url(url) else None

    return None


def _try_tabs_file(session_dir: str, max_stale_s: float = 300) -> str | None:
    sess_path = Path(session_dir)
    tabs_files = sorted(
        sess_path.glob("Tabs_*"), key=lambda f: f.stat().st_mtime, reverse=True
    )
    for tf in tabs_files:
        if tf.stat().st_size == 0:
            continue
        if not _is_recent(tf, max_stale_s):
            continue
        try:
            entries = parse_session_file(str(tf))
            active = [t for t in entries if t["is_active_window"]]
            if active:
                active.sort(key=lambda t: t["window_id"])
                url = active[0]["url"]
                if is_trackable_url(url):
                    return url
            if entries:
                url = entries[0]["url"]
                if is_trackable_url(url):
                    return url
        except Exception:
            continue
    return None

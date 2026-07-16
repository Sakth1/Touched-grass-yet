import logging
import re
import subprocess

from core.collectors.android.package_resolver import resolve as resolve_package

logger = logging.getLogger(__name__)

_PKG_RE = re.compile(r"^\s+Package:\s+(\S+)")
_FG_RE = re.compile(r"^\s+Foreground time:\s+(\d+)")
_LAST_RE = re.compile(r"^\s+Last time used:\s+(.+)")
_FIRST_RE = re.compile(r"^\s+First time used:\s+(.+)")

_UsageStatsManager = None
_UsageEvents = None
_PythonActivity = None
_mActivity = None
_manager = None


def _ensure_jnius():
    global _UsageStatsManager, _UsageEvents, _PythonActivity, _mActivity, _manager
    if _manager is not None:
        return True
    try:
        from jnius import autoclass
        _UsageStatsManager = autoclass("android.app.usage.UsageStatsManager")
        _UsageEvents = autoclass("android.app.usage.UsageEvents")
        _PythonActivity = autoclass("org.kivy.android.PythonActivity")
        _mActivity = _PythonActivity.mActivity
        _manager = _mActivity.getSystemService("usagestats")
        return True
    except Exception:
        logger.warning("jnius unavailable — falling back to dumpsys")
        return False


def check_usage_stats_permission() -> bool:
    try:
        from jnius import autoclass
    except ImportError:
        logger.warning("pyjnius not available — cannot check Usage Access permission")
        return False
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        appOps = PythonActivity.mActivity.getSystemService("appops")
        Process = autoclass("android.os.Process")
        mode = appOps.checkOpNoThrow(
            "android:get_usage_stats",
            Process.myUid(),
            PythonActivity.mActivity.getPackageName(),
        )
        return mode == 0
    except Exception as e:
        logger.warning("Failed to check Usage Access permission: %s", e)
        return False


def _query_jnius(begin_ms: int, end_ms: int) -> dict:
    if not _ensure_jnius():
        return {}
    try:
        stats_list = _manager.queryUsageStats(0, begin_ms, end_ms)
        if stats_list is None:
            return {}
        result = {}
        for i in range(stats_list.size()):
            stat = stats_list.get(i)
            pkg = stat.getPackageName()
            result[pkg] = {
                "package_name": pkg,
                "total_time_foreground_ms": stat.getTotalTimeInForeground(),
                "last_time_used_ms": stat.getLastTimeUsed(),
                "first_time_used_ms": stat.getFirstTimeUsed(),
                "app_name": resolve_package(pkg),
            }
        return result
    except Exception as e:
        if "SecurityException" in type(e).__name__:
            logger.warning("Usage Access permission not granted — jnius query failed")
        else:
            logger.exception("jnius queryUsageStats failed")
        return {}


def _dumpsys_usage_stats(begin_ms: int, end_ms: int) -> dict:
    try:
        result = subprocess.run(
            ["dumpsys", "usagestats"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception as e:
        logger.debug("dumpsys usagestats failed: %s", e)
        return {}

    if result.returncode != 0:
        return {}
    if "SecurityException" in result.stderr or "Permission" in result.stderr:
        logger.warning("Usage Access permission not granted — dumpsys denied")
        return {}

    stats = {}
    pkg = None
    fg_ms = 0
    last_used = 0
    first_used = 0

    for line in result.stdout.splitlines():
        m = _PKG_RE.match(line)
        if m:
            if pkg is not None:
                stats[pkg] = {
                    "package_name": pkg,
                    "total_time_foreground_ms": fg_ms,
                    "last_time_used_ms": last_used,
                    "first_time_used_ms": first_used,
                    "app_name": resolve_package(pkg),
                }
            pkg = m.group(1)
            fg_ms = 0
            last_used = 0
            first_used = 0
            continue

        m = _FG_RE.match(line)
        if m and pkg:
            fg_ms = int(m.group(1))
            continue

        m = _LAST_RE.match(line)
        if m and pkg:
            last_used = _parse_dumpsys_time(m.group(1))
            continue

        m = _FIRST_RE.match(line)
        if m and pkg:
            first_used = _parse_dumpsys_time(m.group(1))
            continue

    if pkg is not None:
        stats[pkg] = {
            "package_name": pkg,
            "total_time_foreground_ms": fg_ms,
            "last_time_used_ms": last_used,
            "first_time_used_ms": first_used,
            "app_name": resolve_package(pkg),
        }

    return stats


def _parse_dumpsys_time(time_str: str) -> int:
    try:
        parts = time_str.strip().split()
        if not parts:
            return 0
        date_part = parts[0]
        time_part = parts[1] if len(parts) > 1 else "00:00:00"
        import datetime
        dt = datetime.datetime.strptime(f"{date_part} {time_part}", "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp() * 1000)
    except Exception:
        return 0


def query_usage_stats(begin_ms: int, end_ms: int) -> dict:
    result = _query_jnius(begin_ms, end_ms)
    if result:
        return result
    result = _dumpsys_usage_stats(begin_ms, end_ms)
    if result:
        logger.debug("dumpsys returned %d packages", len(result))
    return result


def query_usage_events(begin_ms: int, end_ms: int) -> list:
    if not _ensure_jnius():
        return []
    try:
        events = _manager.queryEvents(begin_ms, end_ms)
        if events is None:
            return []
        result = []
        event = _UsageEvents.Event()
        while events.hasNextEvent():
            events.getNextEvent(event)
            result.append({
                "package_name": event.getPackageName(),
                "event_type": event.getEventType(),
                "time_stamp_ms": event.getTimeStamp(),
            })
        return result
    except Exception as e:
        if "SecurityException" in type(e).__name__:
            logger.warning("Usage Access permission not granted — cannot query usage events")
        else:
            logger.exception("queryUsageEvents failed")
        return []


def get_current_time_ms() -> int:
    import time
    return int(time.time() * 1000)

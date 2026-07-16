import logging

from core.collectors.android.package_resolver import resolve as resolve_package

logger = logging.getLogger(__name__)

_INTERVAL_DAILY = 0

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
    except ImportError:
        logger.warning("pyjnius not available — cannot access Android UsageStatsManager")
        return False

    _UsageStatsManager = autoclass("android.app.usage.UsageStatsManager")
    _UsageEvents = autoclass("android.app.usage.UsageEvents")
    _PythonActivity = autoclass("org.kivy.android.PythonActivity")
    _mActivity = _PythonActivity.mActivity
    _manager = _mActivity.getSystemService("usagestats")
    return True


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


def query_usage_stats(begin_ms: int, end_ms: int) -> dict:
    if not _ensure_jnius():
        return {}

    try:
        stats_list = _manager.queryUsageStats(_INTERVAL_DAILY, begin_ms, end_ms)
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
            logger.warning("Usage Access permission not granted — cannot query usage stats")
        else:
            logger.exception("queryUsageStats failed")
        return {}


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

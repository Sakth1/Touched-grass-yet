import logging
import os

from core.collectors.android.package_resolver import resolve as resolve_package

logger = logging.getLogger(__name__)

_Context = None
_UsageStatsManager = None
_UsageEvents = None
_activity = None
_manager = None


def _get_activity():
    global _activity
    if _activity is not None:
        return _activity
    activity_host_class = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    if not activity_host_class:
        logger.warning("MAIN_ACTIVITY_HOST_CLASS_NAME not set — not running under Flet/Android?")
        return None
    try:
        from jnius import autoclass
        activity_host = autoclass(activity_host_class)
        _activity = activity_host.mActivity
        return _activity
    except Exception as e:
        logger.warning("Failed to get Android activity via jnius: %s", e)
        return None


def _ensure_jnius():
    global _Context, _UsageStatsManager, _UsageEvents, _manager
    if _manager is not None:
        return True
    try:
        from jnius import autoclass
        _Context = autoclass("android.content.Context")
        _UsageStatsManager = autoclass("android.app.usage.UsageStatsManager")
        _UsageEvents = autoclass("android.app.usage.UsageEvents")

        activity = _get_activity()
        if activity is None:
            return False
        _manager = activity.getSystemService(_Context.USAGE_STATS_SERVICE)
        return True
    except Exception:
        logger.warning("jnius unavailable")
        return False


def check_usage_stats_permission() -> bool:
    try:
        activity = _get_activity()
        if activity is None:
            return False
        from jnius import autoclass
        AppOpsManager = autoclass("android.app.AppOpsManager")
        Process = autoclass("android.os.Process")
        Context = autoclass("android.content.Context")
        appOps = activity.getSystemService(Context.APP_OPS_SERVICE)
        mode = appOps.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            Process.myUid(),
            activity.getPackageName(),
        )
        return mode == AppOpsManager.MODE_ALLOWED
    except Exception as e:
        logger.warning("Failed to check Usage Access permission: %s", e)
        return False


def _query_jnius(begin_ms: int, end_ms: int) -> dict:
    if not _ensure_jnius():
        return {}
    try:
        stats_list = _manager.queryUsageStats(0, begin_ms, end_ms)
        if stats_list is None:
            logger.debug("queryUsageStats returned None for range %d-%d", begin_ms, end_ms)
            return {}
        result = {}
        for i in range(stats_list.size()):
            stat = stats_list.get(i)
            pkg = stat.getPackageName()
            result[pkg] = {
                "package_name": pkg,
                "total_time_foreground_ms": stat.getTotalTimeInForeground(),
                "last_time_used_ms": stat.getLastTimeUsed(),
                "first_time_used_ms": stat.getFirstTimeStamp(),
                "app_name": resolve_package(pkg),
            }
        return result
    except Exception as e:
        if "SecurityException" in type(e).__name__:
            logger.warning("Usage Access permission not granted — jnius query failed")
        else:
            logger.exception("jnius queryUsageStats failed")
        return {}


def query_usage_stats(begin_ms: int, end_ms: int) -> dict:
    return _query_jnius(begin_ms, end_ms)


def query_usage_events(begin_ms: int, end_ms: int) -> list:
    if not _ensure_jnius():
        return []
    try:
        events = _manager.queryEvents(begin_ms, end_ms)
        if events is None:
            logger.debug("queryEvents returned None for range %d-%d", begin_ms, end_ms)
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


def open_usage_access_settings() -> bool:
    try:
        activity = _get_activity()
        if activity is None:
            return False
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        Settings = autoclass("android.provider.Settings")
        intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
        intent.addFlags(Intent.FLAG_ACTIVITY_NO_HISTORY)
        activity.startActivity(intent)
        return True
    except Exception:
        logger.exception("Failed to open usage access settings via jnius")
        import subprocess
        try:
            subprocess.run(
                ["am", "start", "-a", "android.settings.USAGE_ACCESS_SETTINGS", "--user", "0"],
                capture_output=True, text=True, timeout=5,
            )
            return True
        except Exception as e2:
            logger.error("Failed to open usage access settings via am: %s", e2)
            return False

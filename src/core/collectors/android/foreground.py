import logging

from utils.models import Tick, WatcherConfig
from core.collectors.android.usage_stats import (
    query_usage_stats,
    query_usage_events,
    get_current_time_ms,
)
from core.collectors.android.package_resolver import resolve as resolve_package

logger = logging.getLogger(__name__)

_EVENT_TYPE_RESUMED = 1
_EVENT_TYPE_PAUSED = 2

_MS_PER_S = 1000
_FIRST_TICK_EVENT_WINDOW_MS = 120_000
_FIRST_TICK_EVENT_BUFFER_MS = 30_000


class AndroidForegroundWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="android_foreground",
            interval_s=60.0,
            enabled=True,
        )
        self._last_foreground_ms: dict[str, int] = {}

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()
        day_start_ms = _day_start_ms(now_ms)
        stats = query_usage_stats(day_start_ms, now_ms)
        if not stats:
            logger.debug("No usage stats returned")
            return None

        if not self._last_foreground_ms:
            _init_baseline(stats, self._last_foreground_ms)
            foreground_pkg = _resolve_initial_foreground(now_ms)
            if foreground_pkg:
                logger.debug("First tick — initial foreground from events: %s", foreground_pkg)
                return Tick(
                    watcher="android_foreground",
                    data={
                        "package": foreground_pkg,
                        "app_name": resolve_package(foreground_pkg),
                        "source": "events",
                    },
                )
            logger.debug("First tick — initialized baseline, waiting for next tick")
            return None

        deltas = _compute_deltas(stats, self._last_foreground_ms)
        if not deltas:
            logger.debug("No foreground-time deltas since last poll")
            return None

        top_pkg = max(deltas, key=lambda p: deltas[p]["delta_ms"])

        return Tick(
            watcher="android_foreground",
            data={
                "package": top_pkg,
                "app_name": stats[top_pkg]["app_name"],
                "deltas": deltas,
                "source": "delta",
            },
        )


def _day_start_ms(now_ms: int) -> int:
    import datetime
    dt = datetime.datetime.fromtimestamp(now_ms / _MS_PER_S, tz=datetime.timezone.utc)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp() * _MS_PER_S)


def _init_baseline(
    stats: dict[str, dict],
    last_foreground_ms: dict[str, int],
) -> None:
    for pkg, stat in stats.items():
        last_foreground_ms[pkg] = stat["total_time_foreground_ms"]


def _compute_deltas(
    stats: dict[str, dict],
    last_foreground_ms: dict[str, int],
) -> dict[str, dict]:
    deltas = {}
    for pkg, stat in stats.items():
        current = stat["total_time_foreground_ms"]
        last = last_foreground_ms.get(pkg, 0)
        delta_ms = current - last
        if delta_ms > 0:
            deltas[pkg] = {
                "delta_ms": delta_ms,
                "delta_s": round(delta_ms / _MS_PER_S, 2),
                "app_name": stat["app_name"],
            }
            last_foreground_ms[pkg] = current
    return deltas


def _resolve_initial_foreground(now_ms: int) -> str | None:
    begin_ms = now_ms - _FIRST_TICK_EVENT_WINDOW_MS
    end_ms = now_ms - _FIRST_TICK_EVENT_BUFFER_MS
    if end_ms <= begin_ms:
        return None

    raw_events = query_usage_events(begin_ms, end_ms)
    if not raw_events:
        return None

    active_pkg = None
    for ev in raw_events:
        if ev["event_type"] == _EVENT_TYPE_RESUMED:
            active_pkg = ev["package_name"]
        elif ev["event_type"] == _EVENT_TYPE_PAUSED:
            if active_pkg == ev["package_name"]:
                active_pkg = None

    return active_pkg

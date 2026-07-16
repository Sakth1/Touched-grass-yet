import logging
import time

from utils.models import Tick, WatcherConfig
from core.collectors.android.usage_stats import (
    query_usage_stats,
    query_usage_events,
    get_current_time_ms,
)

logger = logging.getLogger(__name__)

_EVENT_TYPE_RESUMED = 1
_EVENT_TYPE_PAUSED = 2

_MS_PER_S = 1000
_EVENT_POLL_INTERVAL = 5
_EVENT_TRUNCATION_BUFFER_MS = 5 * 60 * 1000
_EVENT_WINDOW_MS = 10 * 60 * 1000


class AndroidForegroundWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="android_foreground",
            interval_s=60.0,
            enabled=True,
        )
        self._last_foreground_ms: dict[str, int] = {}
        self._last_event_time_ms: int = 0
        self._ticks_since_event_poll: int = 0

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()
        day_start_ms = _day_start_ms(now_ms)
        stats = query_usage_stats(day_start_ms, now_ms)
        if not stats:
            return None

        deltas = _compute_deltas(stats, self._last_foreground_ms)
        if not deltas:
            return None

        top_pkg = max(deltas, key=lambda p: deltas[p]["delta_ms"])

        data: dict = {
            "package": top_pkg,
            "app_name": stats[top_pkg]["app_name"],
            "deltas": deltas,
            "source": "delta",
        }

        self._ticks_since_event_poll += 1
        if self._ticks_since_event_poll >= _EVENT_POLL_INTERVAL:
            self._ticks_since_event_poll = 0
            events = self._collect_events(now_ms)
            if events:
                data["events"] = events
                data["source"] = "delta+events"

        return Tick(
            watcher="android_foreground",
            data=data,
        )

    def _collect_events(self, now_ms: int) -> list:
        if self._last_event_time_ms == 0:
            self._last_event_time_ms = now_ms - _EVENT_WINDOW_MS
            return []

        begin_ms = self._last_event_time_ms - _EVENT_WINDOW_MS
        end_ms = now_ms - _EVENT_TRUNCATION_BUFFER_MS
        if end_ms <= begin_ms:
            return []

        raw_events = query_usage_events(begin_ms, end_ms)
        self._last_event_time_ms = now_ms
        if not raw_events:
            return []

        transitions = []
        for ev in raw_events:
            if ev["event_type"] in (_EVENT_TYPE_RESUMED, _EVENT_TYPE_PAUSED):
                transitions.append({
                    "package": ev["package_name"],
                    "type": "resumed" if ev["event_type"] == _EVENT_TYPE_RESUMED else "paused",
                    "timestamp_ms": ev["time_stamp_ms"],
                })
        return transitions


def _day_start_ms(now_ms: int) -> int:
    import datetime
    dt = datetime.datetime.fromtimestamp(now_ms / _MS_PER_S, tz=datetime.timezone.utc)
    day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(day_start.timestamp() * _MS_PER_S)


def _compute_deltas(
    stats: dict,
    last_foreground_ms: dict[str, int],
) -> dict:
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

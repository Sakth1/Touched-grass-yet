import logging

from core.collectors.android.usage_stats import (
    _EVENT_TYPE_RESUMED,
    check_usage_stats_permission,
    get_current_time_ms,
    is_screen_on,
    query_usage_events,
)
from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)

_EVENT_LOOKBACK_SECONDS = 300


class AndroidAfkWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="android_afk",
            interval_s=5.0,
            enabled=True,
        )
        self._permission_lost = False

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()

        screen_on = is_screen_on()
        if not screen_on:
            return Tick(
                watcher="android_afk",
                data={"present": False},
            )

        if not check_usage_stats_permission():
            if not self._permission_lost:
                logger.warning("Usage Stats permission lost — user presence fallback to screen state")
                self._permission_lost = True
            return Tick(
                watcher="android_afk",
                data={"present": True},
            )

        if self._permission_lost:
            logger.info("Usage Stats permission restored — user presence watcher resumed")
            self._permission_lost = False

        present = self._check_presence(now_ms)

        return Tick(
            watcher="android_afk",
            data={"present": present},
        )

    def _check_presence(self, now_ms: int) -> bool:
        lookback_ms = _EVENT_LOOKBACK_SECONDS * 1000
        events = query_usage_events(now_ms - lookback_ms, now_ms)
        for ev in events:
            if ev["event_type"] == _EVENT_TYPE_RESUMED:
                return True
        return False

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

_EVENT_LOOKBACK_SECONDS = 600
_ACTIVE_THRESHOLD = 60
_IDLE_THRESHOLD = 300


class AndroidAfkWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="android_afk",
            interval_s=5.0,
            enabled=True,
        )
        self._last_usage_ms: int | None = None
        self._permission_lost = False

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()

        if not check_usage_stats_permission():
            if not self._permission_lost:
                logger.warning("Usage Stats permission lost — AFK watcher using screen state only")
                self._permission_lost = True
                self._last_usage_ms = None
            screen_on = is_screen_on()
            status = "away" if not screen_on else "active"
            return Tick(
                watcher="android_afk",
                data={"status": status, "idle_seconds": 0.0},
            )

        if self._permission_lost:
            logger.info("Usage Stats permission restored — AFK watcher resumed")
            self._permission_lost = False

        screen_on = is_screen_on()

        last_event_ms = self._query_last_event_ms(now_ms)

        if screen_on and last_event_ms is not None:
            self._last_usage_ms = max(last_event_ms, self._last_usage_ms or 0)

        reference_ms = self._last_usage_ms or now_ms
        idle_seconds = max(0.0, (now_ms - reference_ms) / 1000.0)
        status = self._compute_status(idle_seconds, screen_on)

        return Tick(
            watcher="android_afk",
            data={
                "status": status,
                "idle_seconds": idle_seconds,
            },
        )

    def _query_last_event_ms(self, now_ms: int) -> int | None:
        lookback_ms = _EVENT_LOOKBACK_SECONDS * 1000
        events = query_usage_events(now_ms - lookback_ms, now_ms)
        last_resume = None
        for ev in events:
            if ev["event_type"] == _EVENT_TYPE_RESUMED:
                resume_time = ev["time_stamp_ms"]
                if last_resume is None or resume_time > last_resume:
                    last_resume = resume_time
        return last_resume

    @staticmethod
    def _compute_status(idle_seconds: float, screen_on: bool) -> str:
        if not screen_on:
            return "away"
        if idle_seconds > _IDLE_THRESHOLD:
            return "away"
        if idle_seconds > _ACTIVE_THRESHOLD:
            return "idle"
        return "active"

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
_EVENT_WINDOW_OVERLAP_MS = 120_000
_EVENT_END_BUFFER_MS = 15_000


class AndroidForegroundWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="android_foreground",
            interval_s=60.0,
            enabled=True,
        )
        self._last_tick_ms: int | None = None
        self._previous_app: str | None = None
        self._last_foreground_ms: dict[str, int] = {}
        self._active_events: dict[str, int] = {}

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()

        if self._last_tick_ms is None:
            return self._first_tick(now_ms)

        return self._subsequent_tick(now_ms)

    def _first_tick(self, now_ms: int) -> Tick | None:
        day_start_ms = _day_start_ms(now_ms)
        stats = query_usage_stats(day_start_ms, now_ms)
        if stats:
            _init_baseline(stats, self._last_foreground_ms)

        foreground_pkg = _resolve_initial_foreground(now_ms)
        self._last_tick_ms = now_ms

        if foreground_pkg:
            self._previous_app = foreground_pkg
            app_name = resolve_package(foreground_pkg)
            logger.info("foreground [events]: %s", app_name)
            return Tick(
                watcher="android_foreground",
                data={
                    "package": foreground_pkg,
                    "app_name": app_name,
                    "durations": {},
                    "source": "events",
                },
            )

        if stats:
            logger.info("foreground [baseline]: initialized %d packages", len(stats))
            return None

        logger.debug("No usage stats or events on first tick")
        return None

    def _subsequent_tick(self, now_ms: int) -> Tick | None:
        durations, current_pkg, source = self._try_events(now_ms)

        if current_pkg is None:
            durations, current_pkg, source = self._try_stats(now_ms)

        self._last_tick_ms = now_ms

        if current_pkg is None:
            logger.info("foreground [idle]: no app activity this interval")
            return None

        self._previous_app = current_pkg
        app_name = resolve_package(current_pkg)

        parts = sorted(durations.items(), key=lambda x: x[1]["duration_ms"], reverse=True)
        logger.info(
            "foreground [%ds]: %s",
            int(self.config.interval_s),
            ", ".join(f"{d['app_name']} {d['duration_s']}s" for _, d in parts),
        )

        return Tick(
            watcher="android_foreground",
            data={
                "package": current_pkg,
                "app_name": app_name,
                "durations": durations,
                "source": source,
            },
        )

    def _try_events(self, now_ms: int) -> tuple[dict, str | None, str]:
        begin_ms = self._last_tick_ms - _EVENT_WINDOW_OVERLAP_MS
        end_ms = now_ms - _EVENT_END_BUFFER_MS
        if end_ms <= begin_ms:
            return {}, None, "events"

        raw_events = query_usage_events(begin_ms, end_ms)
        if not raw_events:
            return {}, None, "events"

        active_start: dict[str, int] = dict(self._active_events)
        durations: dict[str, int] = {}

        for ev in raw_events:
            pkg = ev["package_name"]
            ev_type = ev["event_type"]
            ts = ev["time_stamp_ms"]

            if ev_type == _EVENT_TYPE_RESUMED:
                if pkg in active_start:
                    _accumulate_clipped(durations, pkg, active_start[pkg], ts, self._last_tick_ms)
                active_start[pkg] = ts

            elif ev_type == _EVENT_TYPE_PAUSED:
                if pkg in active_start:
                    _accumulate_clipped(durations, pkg, active_start[pkg], ts, self._last_tick_ms)
                    del active_start[pkg]

        self._active_events = dict(active_start)

        for pkg, start_ms in list(active_start.items()):
            _accumulate_clipped(durations, pkg, start_ms, end_ms, self._last_tick_ms)

        current_pkg = None
        for ev in reversed(raw_events):
            pkg = ev["package_name"]
            if ev["event_type"] == _EVENT_TYPE_RESUMED and pkg in active_start:
                current_pkg = pkg
                break

        if current_pkg is None:
            current_pkg = self._previous_app

        result = _build_result(durations)
        return result, current_pkg, "events"

    def _try_stats(self, now_ms: int) -> tuple[dict, str | None, str]:
        day_start_ms = _day_start_ms(now_ms)
        stats = query_usage_stats(day_start_ms, now_ms)
        if not stats:
            return {}, None, "delta"

        stale = self._last_foreground_ms.keys() - stats.keys()
        if stale:
            for pkg in stale:
                del self._last_foreground_ms[pkg]

        deltas = _compute_deltas(stats, self._last_foreground_ms)
        if not deltas:
            return {}, None, "delta"

        top_pkg = max(deltas, key=lambda p: deltas[p]["delta_ms"])
        durations = {}
        for pkg, d in deltas.items():
            durations[pkg] = {
                "duration_ms": d["delta_ms"],
                "duration_s": d["delta_s"],
                "app_name": d["app_name"],
            }

        return durations, top_pkg, "delta"


def _day_start_ms(now_ms: int) -> int:
    import datetime
    local_dt = datetime.datetime.fromtimestamp(now_ms / _MS_PER_S)
    local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    return int(local_midnight.timestamp() * _MS_PER_S)


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


def _accumulate_clipped(
    durations: dict[str, int],
    pkg: str,
    start_ms: int,
    end_ms: int,
    clip_from_ms: int,
) -> None:
    seg_start = max(start_ms, clip_from_ms)
    delta = max(end_ms, seg_start) - seg_start
    if delta > 0:
        durations[pkg] = durations.get(pkg, 0) + delta


def _build_result(durations: dict[str, int]) -> dict[str, dict]:
    return {
        pkg: {
            "duration_ms": ms,
            "duration_s": round(ms / _MS_PER_S, 2),
            "app_name": resolve_package(pkg),
        }
        for pkg, ms in durations.items()
        if ms > 0
    }


def _resolve_initial_foreground(now_ms: int) -> str | None:
    begin_ms = now_ms - _EVENT_WINDOW_OVERLAP_MS
    end_ms = now_ms - _EVENT_END_BUFFER_MS
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

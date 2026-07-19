import logging

from core.collectors.android.package_resolver import resolve as resolve_package
from core.collectors.android.usage_stats import (
    _EVENT_TYPE_PAUSED,
    _EVENT_TYPE_RESUMED,
    check_usage_stats_permission,
    get_current_time_ms,
    is_screen_on,
    query_usage_events,
    query_usage_stats,
)
from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)

_MS_PER_S = 1000
_EVENT_WINDOW_OVERLAP_MS = 120_000
_EVENT_END_BUFFER_MS = 2_000


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
        self._session_reported: dict[tuple[str, int], int] = {}
        self._permission_lost = False

    async def tick(self) -> Tick | None:
        now_ms = get_current_time_ms()

        if not check_usage_stats_permission():
            if not self._permission_lost:
                logger.warning("Usage Stats permission lost — pausing foreground watcher")
                self._permission_lost = True
                self._last_foreground_ms.clear()
                self._active_events.clear()
                self._session_reported.clear()
                self._last_tick_ms = None
                self._previous_app = None
            return None

        if self._permission_lost:
            logger.info("Usage Stats permission restored — resuming foreground watcher")
            self._permission_lost = False

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
            top_pkg = max(stats, key=lambda p: stats[p]["total_time_foreground_ms"])
            self._previous_app = top_pkg
            logger.info(
                "foreground [baseline]: initialized %d packages, previous=%s",
                len(stats),
                stats[top_pkg]["app_name"],
            )
            return None

        logger.debug("No usage stats or events on first tick")
        return None

    def _subsequent_tick(self, now_ms: int) -> Tick | None:
        durations, current_pkg, source = self._try_events(now_ms)

        if current_pkg is None:
            durations, current_pkg, source = self._try_stats(now_ms)
        else:
            self._sync_stats(now_ms)

        self._last_tick_ms = now_ms

        if current_pkg is None:
            if is_screen_on() and self._previous_app is not None:
                current_pkg = self._previous_app
                source = "stale"
                logger.debug("foreground [stale]: %s (screen on, no events)", current_pkg)
            else:
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

    def _sync_stats(self, now_ms: int) -> None:
        day_start_ms = _day_start_ms(now_ms)
        stats = query_usage_stats(day_start_ms, now_ms)
        if not stats:
            return
        stale = self._last_foreground_ms.keys() - stats.keys()
        for pkg in stale:
            del self._last_foreground_ms[pkg]
        for pkg, stat in stats.items():
            self._last_foreground_ms[pkg] = stat["total_time_foreground_ms"]

    def _try_events(self, now_ms: int) -> tuple[dict, str | None, str]:
        begin_ms = self._last_tick_ms - _EVENT_WINDOW_OVERLAP_MS
        end_ms = now_ms - _EVENT_END_BUFFER_MS
        if end_ms <= begin_ms:
            self._cleanup_session_reported({})
            return {}, None, "events"

        raw_events = query_usage_events(begin_ms, end_ms)
        if not raw_events:
            self._cleanup_session_reported(self._active_events)
            self._sync_stats(now_ms)
            return {}, None, "events"

        active_start: dict[str, int] = dict(self._active_events)
        durations: dict[str, int] = {}

        for ev in raw_events:
            pkg = ev["package_name"]
            ev_type = ev["event_type"]
            ts = ev["time_stamp_ms"]

            if ev_type == _EVENT_TYPE_RESUMED:
                if pkg in active_start:
                    seg_key = (pkg, active_start[pkg])
                    added = _accumulate_clipped(durations, pkg, active_start[pkg], ts, self._last_tick_ms)
                    self._session_reported[seg_key] = self._session_reported.get(seg_key, 0) + added
                active_start[pkg] = ts

            elif ev_type == _EVENT_TYPE_PAUSED:
                if pkg in active_start:
                    seg_key = (pkg, active_start[pkg])
                    total = ts - active_start[pkg]
                    already = self._session_reported.get(seg_key, 0)
                    remaining = total - already
                    if remaining > 0:
                        durations[pkg] = durations.get(pkg, 0) + remaining
                    del active_start[pkg]
                    self._session_reported.pop(seg_key, None)

        self._active_events = dict(active_start)

        for pkg, start_ms in list(active_start.items()):
            seg_key = (pkg, start_ms)
            added = _accumulate_clipped(durations, pkg, start_ms, end_ms, self._last_tick_ms)
            self._session_reported[seg_key] = self._session_reported.get(seg_key, 0) + added

        self._cleanup_session_reported(active_start)
        self._sync_stats(now_ms)

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

    def _cleanup_session_reported(self, active_start: dict[str, int]) -> None:
        for key in list(self._session_reported):
            if key[0] not in active_start or active_start[key[0]] != key[1]:
                del self._session_reported[key]

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
    try:
        local_dt = datetime.datetime.fromtimestamp(now_ms / _MS_PER_S)
        local_midnight = local_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(local_midnight.timestamp() * _MS_PER_S)
    except (OSError, OverflowError, ValueError):
        logger.debug("Failed to compute day start for %d, defaulting to now", now_ms)
        return now_ms


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
) -> int:
    seg_start = max(start_ms, clip_from_ms)
    delta = max(end_ms, seg_start) - seg_start
    if delta > 0:
        durations[pkg] = durations.get(pkg, 0) + delta
    return delta


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

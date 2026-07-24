import logging
from datetime import datetime, timezone
from typing import Callable

from core.storage import Storage
from utils.models import Observation

logger = logging.getLogger(__name__)

MAX_IDLE_GAP_S = 300.0
DEFAULT_POLL_INTERVAL_S = 5.0

SESSION_SOURCE_PULSE = "pulse"
SESSION_SOURCE_EVENTS = "events"
SESSION_SOURCE_DELTA = "delta"
SESSION_SOURCE_STALE = "stale"


def _app_key_fn_windows(obs: Observation) -> str:
    return obs.data.get("app", "unknown")


def _app_key_fn_android(obs: Observation) -> str:
    return obs.data.get("package", "unknown")


def _source_from_obs(obs: Observation) -> str:
    return obs.data.get("source", SESSION_SOURCE_EVENTS)


_WATCHER_CONFIG: dict[str, dict] = {
    "foreground": {
        "app_key_fn": _app_key_fn_windows,
        "poll_interval_s": 2.0,
        "merge_title_changes": True,
    },
    "android_foreground": {
        "app_key_fn": _app_key_fn_android,
        "poll_interval_s": 60.0,
        "merge_title_changes": True,
    },
}


def sessionize_observations(
    observations: list[Observation],
    watcher: str,
    max_idle_gap: float = MAX_IDLE_GAP_S,
) -> list[dict]:
    if not observations:
        return []

    cfg = _WATCHER_CONFIG.get(watcher)
    if cfg is None:
        logger.warning("No sessionizer config for watcher %s", watcher)
        return []

    app_key_fn = cfg["app_key_fn"]
    poll_interval = cfg["poll_interval_s"]

    sorted_obs = sorted(observations, key=lambda o: o.timestamp)
    sessions: list[dict] = []
    current_start: datetime | None = None
    current_app_key: str | None = None
    current_obs: list[Observation] = []
    current_sources: set[str] = set()

    for obs in sorted_obs:
        app_key = app_key_fn(obs)

        if current_start is None:
            current_start = obs.timestamp
            current_app_key = app_key
            current_obs = [obs]
            current_sources = {_source_from_obs(obs)}
            continue

        gap = (obs.timestamp - current_start).total_seconds() if current_start else 0.0

        if app_key == current_app_key:
            gap_from_last = (obs.timestamp - current_obs[-1].timestamp).total_seconds()
            if gap_from_last <= max_idle_gap:
                current_obs.append(obs)
                current_sources.add(_source_from_obs(obs))
                continue
            else:
                pass

        end_ts_float = _to_epoch(current_obs[-1].timestamp) + poll_interval
        start_ts_float = _to_epoch(current_start)
        duration_s = end_ts_float - start_ts_float

        sessions.append(_build_session(
            watcher=watcher,
            start_ts=start_ts_float,
            end_ts=end_ts_float,
            duration_s=max(0.0, duration_s),
            app_key=current_app_key,
            observations=current_obs,
            sources=current_sources,
        ))

        current_start = obs.timestamp
        current_app_key = app_key
        current_obs = [obs]
        current_sources = {_source_from_obs(obs)}

    if current_start is not None and current_obs:
        end_ts_float = _to_epoch(current_obs[-1].timestamp) + poll_interval
        start_ts_float = _to_epoch(current_start)
        duration_s = end_ts_float - start_ts_float

        sessions.append(_build_session(
            watcher=watcher,
            start_ts=start_ts_float,
            end_ts=end_ts_float,
            duration_s=max(0.0, duration_s),
            app_key=current_app_key,
            observations=current_obs,
            sources=current_sources,
        ))

    return sessions


def _build_session(
    watcher: str,
    start_ts: float,
    end_ts: float,
    duration_s: float,
    app_key: str,
    observations: list[Observation],
    sources: set[str],
) -> dict:
    source_list = sorted(sources)
    source_tag = source_list[0] if source_list else SESSION_SOURCE_PULSE

    if watcher == "android_foreground":
        total_duration_ms = 0
        for obs in observations:
            durs = obs.data.get("durations", {})
            for pkg, info in durs.items():
                if pkg == app_key or info.get("app_name") == app_key:
                    total_duration_ms += info.get("duration_ms", 0)
        if total_duration_ms > 0:
            duration_s = round(total_duration_ms / 1000.0, 2)

    merged_title = None
    for obs in observations:
        title = obs.data.get("title")
        if title:
            merged_title = title

    merged_data: dict = {"observation_count": len(observations)}
    if watcher == "foreground":
        merged_data["title"] = merged_title
        merged_data["app"] = app_key
        browser_info = None
        for obs in observations:
            bi = obs.data.get("browser")
            if bi:
                browser_info = bi
        if browser_info:
            merged_data["browser"] = browser_info
        for obs in observations:
            pt = obs.data.get("page_title")
            if pt:
                merged_data["page_title"] = pt
            dom = obs.data.get("inferred_domain")
            if dom:
                merged_data["inferred_domain"] = dom
    elif watcher == "android_foreground":
        merged_data["package"] = app_key
        merged_data["app_name"] = observations[-1].data.get("app_name", app_key)
        merged_data["source"] = source_tag
        last_durs = observations[-1].data.get("durations", {})
        if last_durs:
            merged_data["durations"] = last_durs

    return {
        "id": None,
        "watcher": watcher,
        "start_ts": round(start_ts, 2),
        "end_ts": round(end_ts, 2),
        "duration_s": round(duration_s, 2),
        "app_key": app_key,
        "data": merged_data,
        "source": source_tag,
    }


def _to_epoch(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def run_sessionization(storage: Storage, watchers: list[str] | None = None) -> int:
    target_watchers = watchers or ["foreground", "android_foreground"]
    total_sessions = 0

    for watcher in target_watchers:
        raw = storage.get_observations(watcher=watcher)
        if not raw:
            continue

        observations = [
            Observation(
                timestamp=datetime.fromtimestamp(r["timestamp"], tz=timezone.utc),
                watcher=r["watcher"],
                data=r["data"],
            )
            for r in raw
        ]

        sessions = sessionize_observations(observations, watcher)
        for session in sessions:
            existing = storage.get_sessions(
                watcher=watcher,
                since=session["start_ts"],
                until=session["start_ts"] + 1.0,
                app_key=session["app_key"],
            )
            if not existing:
                storage.write_session(session)
                total_sessions += 1

    return total_sessions

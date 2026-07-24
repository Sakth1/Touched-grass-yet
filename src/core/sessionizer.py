import logging

from core.storage import Storage

logger = logging.getLogger(__name__)

MAX_IDLE_GAP_S = 300.0
WINDOWS_POLL_INTERVAL_S = 2.0
ANDROID_POLL_INTERVAL_S = 10.0


def sessionize_from_events(
    storage: Storage,
    platform: str | None = None,
    device_id: str | None = None,
) -> list[dict]:
    events = storage.get_raw_events(
        event_type="foreground_transition",
    )
    if not events:
        return []

    if platform:
        events = [e for e in events if e["platform"] == platform]
        if not events:
            return []

    interval_index = _build_interval_index(
        storage.get_raw_events(event_type="app_usage_interval"),
    )

    sessions: list[dict] = []
    current = None

    for ev in events:
        ts = ev["timestamp"]
        p = ev["payload"]
        app_key = p.get("package") or p.get("app", "unknown")

        if current is not None:
            gap = ts - current.last_ts
            if app_key != current.app_key or gap > MAX_IDLE_GAP_S:
                end_ts = current.last_ts + MAX_IDLE_GAP_S if gap > MAX_IDLE_GAP_S else ts
                _finalize_session(current, end_ts, interval_index, sessions)
                current = _start_session(ev, app_key)
                continue

            if app_key == current.app_key:
                current.last_ts = ts
                _merge_event(current, ev)
                continue

        current = _start_session(ev, app_key)

    if current is not None:
        poll_interval = ANDROID_POLL_INTERVAL_S if current.platform == "android" else WINDOWS_POLL_INTERVAL_S
        end_ts = current.last_ts + poll_interval
        _finalize_session(current, end_ts, interval_index, sessions)

    return sessions


class _SessionAccum:
    __slots__ = (
        "device_id",
        "platform",
        "start_ts",
        "last_ts",
        "app_key",
        "payload",
        "session_type",
    )

    def __init__(self, device_id: str, platform: str, start_ts: float, app_key: str):
        self.device_id = device_id
        self.platform = platform
        self.start_ts = start_ts
        self.last_ts = start_ts
        self.app_key = app_key
        self.payload: dict = {}
        self.session_type = "foreground"


def _start_session(ev: dict, app_key: str) -> _SessionAccum:
    sess = _SessionAccum(
        device_id=ev["device_id"],
        platform=ev["platform"],
        start_ts=ev["timestamp"],
        app_key=app_key,
    )
    _merge_event(sess, ev)
    return sess


def _merge_event(sess: _SessionAccum, ev: dict) -> None:
    p = ev["payload"]
    if sess.platform == "android":
        sess.payload["package"] = p.get("package", app_key_from_sess(sess))
        sess.payload["app_name"] = p.get("app_name", sess.payload.get("app_name", "unknown"))
    else:
        sess.payload["app"] = p.get("app", app_key_from_sess(sess))
        title = p.get("title")
        if title:
            sess.payload["title"] = title
        browser = p.get("browser")
        if browser:
            sess.payload["browser"] = browser
        page_title = p.get("page_title")
        if page_title:
            sess.payload["page_title"] = page_title
        domain = p.get("inferred_domain")
        if domain:
            sess.payload["inferred_domain"] = domain


def app_key_from_sess(sess: _SessionAccum) -> str:
    return sess.app_key


def _build_interval_index(interval_events: list[dict]) -> dict[str, list[dict]]:
    index: dict[str, list[dict]] = {}
    for ev in interval_events:
        intervals = ev["payload"].get("intervals", [])
        ev_ts = ev["timestamp"]
        for interval in intervals:
            pkg = interval.get("package", "unknown")
            index.setdefault(pkg, []).append(
                {
                    "ts": ev_ts,
                    "duration_ms": interval.get("duration_ms", 0),
                }
            )
    return index


def _sum_interval_duration(
    interval_index: dict[str, list[dict]],
    app_key: str,
    start_ts: float,
    end_ts: float,
) -> float | None:
    entries = interval_index.get(app_key)
    if not entries:
        return None
    total_ms = sum(e["duration_ms"] for e in entries if start_ts <= e["ts"] <= end_ts)
    if total_ms <= 0:
        return None
    return round(total_ms / 1000.0, 2)


def _finalize_session(
    sess: _SessionAccum,
    end_ts: float,
    interval_index: dict[str, list[dict]],
    sessions: list[dict],
) -> None:
    start = sess.start_ts
    duration_s = None

    if sess.platform == "android":
        interval_dur = _sum_interval_duration(interval_index, sess.app_key, start, end_ts)
        if interval_dur is not None:
            duration_s = interval_dur

    if duration_s is None:
        duration_s = max(0.0, end_ts - start)

    sessions.append(
        {
            "device_id": sess.device_id,
            "platform": sess.platform,
            "start_ts": round(start, 2),
            "end_ts": round(end_ts, 2),
            "duration_s": round(duration_s, 2),
            "app_key": sess.app_key,
            "payload": dict(sess.payload),
            "session_type": sess.session_type,
        }
    )


def run_sessionization(storage: Storage, platform: str | None = None) -> int:
    sessions = sessionize_from_events(storage, platform=platform)
    count = 0
    for session in sessions:
        existing = storage.get_canonical_sessions(
            app_key=session["app_key"],
            since=session["start_ts"],
            until=session["start_ts"] + 1.0,
        )
        if not existing:
            storage.write_canonical_session(session)
            count += 1
    if count:
        logger.info("Sessionization wrote %d new sessions", count)
    return count

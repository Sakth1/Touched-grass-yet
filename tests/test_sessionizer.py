from unittest.mock import MagicMock

from core.sessionizer import ANDROID_MAX_IDLE_GAP_S, run_sessionization, sessionize_from_events
from core.storage import Storage


def _make_transition(
    ts: float,
    app_key: str,
    platform: str = "android",
    extra_payload: dict | None = None,
) -> dict:
    p = {"package": app_key, "app_name": app_key.capitalize()}
    if platform == "windows":
        p = {"app": app_key, "title": extra_payload.get("title", app_key) if extra_payload else app_key}
        if extra_payload:
            p.update(extra_payload)
    if extra_payload:
        p.update(extra_payload)
    return {
        "device_id": "test-device",
        "platform": platform,
        "event_type": "foreground_transition",
        "timestamp": ts,
        "payload": p,
        "source": "usage_events",
    }


def _make_interval_event(ts: float, intervals: list[dict]) -> dict:
    return {
        "device_id": "test-device",
        "platform": "android",
        "event_type": "app_usage_interval",
        "timestamp": ts,
        "payload": {"intervals": intervals},
        "source": "usage_stats",
    }


class TestEmptyEvents:
    def test_no_events_returns_empty(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.return_value = []

        result = sessionize_from_events(storage)
        assert result == []


class TestSingleSession:
    def test_single_event_creates_one_session(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [_make_transition(1000.0, "com.instagram")],
            [],
        ]

        result = sessionize_from_events(storage)
        assert len(result) == 1
        assert result[0]["app_key"] == "com.instagram"
        assert result[0]["start_ts"] == 1000.0
        assert result[0]["end_ts"] > 1000.0
        assert result[0]["platform"] == "android"

    def test_single_windows_event(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [_make_transition(1000.0, "Code.exe", platform="windows")],
            [],
        ]

        result = sessionize_from_events(storage)
        assert len(result) == 1
        assert result[0]["app_key"] == "Code.exe"
        assert result[0]["platform"] == "windows"


class TestMultiSession:
    def test_two_different_apps_creates_two_sessions(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "com.instagram"),
                _make_transition(1200.0, "com.chrome"),
            ],
            [],
        ]

        result = sessionize_from_events(storage)
        assert len(result) == 2
        assert result[0]["app_key"] == "com.instagram"
        assert result[0]["end_ts"] == 1200.0
        assert result[1]["app_key"] == "com.chrome"

    def test_same_app_consecutive_merges(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "com.instagram"),
                _make_transition(1100.0, "com.instagram"),
                _make_transition(1200.0, "com.chrome"),
            ],
            [],
        ]

        result = sessionize_from_events(storage)
        assert len(result) == 2
        assert result[0]["app_key"] == "com.instagram"
        assert result[0]["start_ts"] == 1000.0
        assert result[0]["end_ts"] == 1200.0


class TestIdleGap:
    def test_large_gap_splits_session(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "com.instagram"),
                _make_transition(2000.0, "com.instagram"),
            ],
            [],
        ]

        assert (2000.0 - 1000.0) > ANDROID_MAX_IDLE_GAP_S

        result = sessionize_from_events(storage)
        assert len(result) == 2
        assert result[0]["app_key"] == "com.instagram"
        assert result[0]["end_ts"] == 1000.0 + ANDROID_MAX_IDLE_GAP_S


class TestAndroidDuration:
    def test_duration_from_interval_events(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "com.instagram"),
                _make_transition(1300.0, "com.chrome"),
            ],
            [
                _make_interval_event(
                    1050.0,
                    [{"package": "com.instagram", "duration_ms": 250000, "app_name": "Instagram"}],
                ),
                _make_interval_event(
                    1150.0,
                    [{"package": "com.instagram", "duration_ms": 50000, "app_name": "Instagram"}],
                ),
            ],
        ]

        result = sessionize_from_events(storage)
        assert len(result) == 2
        insta_session = result[0]
        assert insta_session["app_key"] == "com.instagram"
        assert insta_session["duration_s"] == 300.0  # 250000 + 50000 = 300000 ms

    def test_duration_fallback_when_no_intervals(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "com.instagram"),
                _make_transition(1300.0, "com.chrome"),
            ],
            [],
        ]

        result = sessionize_from_events(storage)
        insta_session = result[0]
        assert insta_session["duration_s"] == 300.0  # fallback: 1300 - 1000


class TestWindowsMetadata:
    def test_windows_title_merged(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(1000.0, "Code.exe", platform="windows", extra_payload={"title": "main.py"}),
                _make_transition(1100.0, "Code.exe", platform="windows", extra_payload={"title": "test.py"}),
                _make_transition(1200.0, "brave.exe", platform="windows", extra_payload={"title": "brave"}),
            ],
            [],
        ]

        result = sessionize_from_events(storage)
        code_session = result[0]
        assert code_session["app_key"] == "Code.exe"
        assert code_session["payload"]["title"] == "test.py"

    def test_windows_browser_domain(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [
                _make_transition(
                    1000.0,
                    "brave.exe",
                    platform="windows",
                    extra_payload={"title": "GitHub", "browser": "Brave", "inferred_domain": "github.com"},
                ),
            ],
            [],
        ]

        result = sessionize_from_events(storage)
        session = result[0]
        assert session["payload"]["browser"] == "Brave"
        assert session["payload"]["inferred_domain"] == "github.com"


class TestPlatformFilter:
    def test_platform_filter_android(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.return_value = [
            _make_transition(1000.0, "com.instagram"),
            _make_transition(1100.0, "Code.exe", platform="windows"),
        ]

        result = sessionize_from_events(storage, platform="android")
        assert len(result) == 1
        assert result[0]["platform"] == "android"

    def test_platform_filter_windows(self):
        storage = MagicMock(spec=Storage)
        storage.get_raw_events.return_value = [
            _make_transition(1000.0, "com.instagram"),
            _make_transition(1100.0, "Code.exe", platform="windows"),
        ]

        result = sessionize_from_events(storage, platform="windows")
        assert len(result) == 1
        assert result[0]["platform"] == "windows"


class TestRunSessionization:
    def test_writes_new_sessions(self):

        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [_make_transition(1000.0, "com.instagram")],
            [],
        ]
        storage.get_canonical_sessions.return_value = []

        count = run_sessionization(storage)
        assert count == 1
        storage.write_canonical_session.assert_called_once()

    def test_skips_existing_sessions(self):

        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [_make_transition(1000.0, "com.instagram")],
            [],
        ]
        storage.get_canonical_sessions.return_value = [{"id": 1}]

        count = run_sessionization(storage)
        assert count == 0
        storage.write_canonical_session.assert_not_called()


class TestRunUrlEnrichment:
    def test_enriches_session_with_url_aggregates(self):
        storage = MagicMock(spec=Storage)
        storage._conn = MagicMock()
        storage.get_canonical_sessions.return_value = [
            {
                "id": 1,
                "device_id": "test-device",
                "platform": "windows",
                "start_ts": 1000.0,
                "end_ts": 1200.0,
                "duration_s": 200.0,
                "app_key": "brave.exe",
                "payload": {"title": "GitHub"},
                "session_type": "foreground",
            }
        ]
        storage.get_url_visits.return_value = [
            {
                "id": 10,
                "device_id": "test-device",
                "event_id": None,
                "session_id": None,
                "url": "https://github.com/user",
                "scheme": "https",
                "host": "github.com",
                "domain": "github.com",
                "path": "/user",
                "extraction_method": "uia",
                "confidence": "high",
                "is_trackable": True,
                "seen_at": 1005.0,
                "collected_at": 1005.0,
            },
            {
                "id": 11,
                "device_id": "test-device",
                "event_id": None,
                "session_id": None,
                "url": "https://github.com/user/repo",
                "scheme": "https",
                "host": "github.com",
                "domain": "github.com",
                "path": "/user/repo",
                "extraction_method": "uia",
                "confidence": "high",
                "is_trackable": True,
                "seen_at": 1010.0,
                "collected_at": 1010.0,
            },
        ]

        from core.sessionizer import run_url_enrichment
        count = run_url_enrichment(storage)

        assert count == 1
        import json
        call_args = storage._conn.execute.call_args
        assert call_args is not None
        sql, params = call_args[0]
        assert "UPDATE sessions" in sql
        payload = json.loads(params[0])
        assert payload["url_count"] == 2
        assert payload["url_first"] == "https://github.com/user"
        assert payload["url_last"] == "https://github.com/user/repo"
        assert payload["domains"] == ["github.com"]
        assert params[1] == 1

    def test_skips_session_with_no_visits(self):
        storage = MagicMock(spec=Storage)
        storage._conn = MagicMock()
        storage.get_canonical_sessions.return_value = [
            {
                "id": 1,
                "device_id": "test-device",
                "platform": "windows",
                "start_ts": 1000.0,
                "end_ts": 1200.0,
                "duration_s": 200.0,
                "app_key": "Code.exe",
                "payload": {},
                "session_type": "foreground",
            }
        ]
        storage.get_url_visits.return_value = []

        from core.sessionizer import run_url_enrichment
        count = run_url_enrichment(storage)

        assert count == 0

    def test_multiple_domains(self):
        storage = MagicMock(spec=Storage)
        storage._conn = MagicMock()
        storage.get_canonical_sessions.return_value = [
            {
                "id": 1,
                "device_id": "test-device",
                "platform": "windows",
                "start_ts": 1000.0,
                "end_ts": 1200.0,
                "duration_s": 200.0,
                "app_key": "brave.exe",
                "payload": {},
                "session_type": "foreground",
            }
        ]
        storage.get_url_visits.return_value = [
            {
                "id": 10, "device_id": "test-device", "event_id": None, "session_id": None,
                "url": "https://github.com/a", "scheme": "https", "host": "github.com",
                "domain": "github.com", "path": "/a", "extraction_method": "uia",
                "confidence": "high", "is_trackable": True, "seen_at": 1005.0, "collected_at": 1005.0,
            },
            {
                "id": 11, "device_id": "test-device", "event_id": None, "session_id": None,
                "url": "https://reddit.com/r/python", "scheme": "https", "host": "reddit.com",
                "domain": "reddit.com", "path": "/r/python", "extraction_method": "uia",
                "confidence": "high", "is_trackable": True, "seen_at": 1010.0, "collected_at": 1010.0,
            },
        ]

        from core.sessionizer import run_url_enrichment
        count = run_url_enrichment(storage)

        assert count == 1
        import json
        sql, params = storage._conn.execute.call_args[0]
        payload = json.loads(params[0])
        assert payload["domains"] == ["github.com", "reddit.com"]

        storage = MagicMock(spec=Storage)
        storage.get_raw_events.side_effect = [
            [_make_transition(1000.0, "com.instagram")],
            [],
        ]
        storage.get_canonical_sessions.return_value = [{"id": 1}]

        count = run_sessionization(storage)
        assert count == 0
        storage.write_canonical_session.assert_not_called()

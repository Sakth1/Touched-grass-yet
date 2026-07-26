import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from core.storage import Storage
from core.storage.analytics_store import AnalyticsStore, TimeGranularity


@pytest.fixture
def analytics_store(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    storage = Storage(db_path=db_path)
    storage.write_event(
        event_type="foreground_transition",
        timestamp=1000.0,
        payload={"app": "Code.exe"},
        source="foreground",
    )
    storage.write_event(
        event_type="foreground_transition",
        timestamp=2000.0,
        payload={"app": "Terminal.exe"},
        source="foreground",
    )
    storage.close()

    store = AnalyticsStore(db_path=db_path)
    yield store
    store.close()


@pytest.fixture
def store_with_sessions(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    storage = Storage(db_path=db_path)
    device_id = "00000000-0000-0000-0000-000000000001"
    storage.write_canonical_session(
        {
            "device_id": device_id,
            "platform": "windows",
            "start_ts": 1000.0,
            "end_ts": 1100.0,
            "duration_s": 100.0,
            "app_key": "Code.exe",
            "payload": {},
            "session_type": "foreground",
        }
    )
    storage.write_canonical_session(
        {
            "device_id": device_id,
            "platform": "windows",
            "start_ts": 1200.0,
            "end_ts": 1400.0,
            "duration_s": 200.0,
            "app_key": "Code.exe",
            "payload": {},
            "session_type": "foreground",
        }
    )
    storage.write_canonical_session(
        {
            "device_id": device_id,
            "platform": "windows",
            "start_ts": 1500.0,
            "end_ts": 1800.0,
            "duration_s": 300.0,
            "app_key": "Terminal.exe",
            "payload": {},
            "session_type": "foreground",
        }
    )
    storage.write_canonical_session(
        {
            "device_id": device_id,
            "platform": "windows",
            "start_ts": 2000.0,
            "end_ts": 2050.0,
            "duration_s": 50.0,
            "app_key": "Code.exe",
            "payload": {},
            "session_type": "foreground",
        }
    )
    storage.close()
    store = AnalyticsStore(db_path=db_path)
    yield store
    store.close()


class TestAnalyticsStoreSkeleton:
    def test_constructor_with_path(self, analytics_store):
        assert analytics_store._conn is not None

    def test_query_attached_data(self, analytics_store):
        rows = analytics_store._conn.execute(
            "SELECT event_type, payload FROM data.raw_events ORDER BY timestamp ASC"
        ).fetchall()
        assert len(rows) == 2
        assert rows[0][0] == "foreground_transition"

    def test_close_is_idempotent(self, analytics_store):
        analytics_store.close()
        analytics_store.close()

    def test_default_db_path(self, tmp_path):
        fake_data_dir = os.path.join(tmp_path, "TouchedGrassYet")
        with patch("core.storage.analytics_store.get_data_dir", return_value=fake_data_dir):
            with patch("core.storage.analytics_store._db_path", return_value=os.path.join(fake_data_dir, "data.db")):
                db_path = os.path.join(fake_data_dir, "data.db")
                os.makedirs(fake_data_dir, exist_ok=True)
                storage = Storage(db_path=db_path)
                storage.write_event(
                    event_type="test",
                    timestamp=500.0,
                    payload={"x": 1},
                    source="test",
                )
                storage.close()

                store = AnalyticsStore()
                rows = store._conn.execute(
                    "SELECT event_type FROM data.raw_events"
                ).fetchall()
                assert len(rows) == 1
                store.close()


@pytest.fixture
def multi_day_sessions(tmp_path):
    db_path = os.path.join(tmp_path, "test.db")
    storage = Storage(db_path=db_path)
    device_id = "00000000-0000-0000-0000-000000000001"

    day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
    day2 = day1 + timedelta(days=1)
    day3 = day1 + timedelta(days=2)

    sessions = [
        {"app_key": "Code.exe", "start_ts": day1.replace(hour=10).timestamp(), "duration_s": 100.0},
        {"app_key": "Terminal.exe", "start_ts": day1.replace(hour=11).timestamp(), "duration_s": 200.0},
        {"app_key": "Code.exe", "start_ts": day2.replace(hour=9).timestamp(), "duration_s": 150.0},
        {"app_key": "Code.exe", "start_ts": day3.replace(hour=14).timestamp(), "duration_s": 50.0},
        {"app_key": "Terminal.exe", "start_ts": day3.replace(hour=15).timestamp(), "duration_s": 100.0},
    ]

    for s in sessions:
        storage.write_canonical_session(
            {
                "device_id": device_id,
                "platform": "windows",
                "start_ts": s["start_ts"],
                "end_ts": s["start_ts"] + s["duration_s"],
                "duration_s": s["duration_s"],
                "app_key": s["app_key"],
                "payload": {},
                "session_type": "foreground",
            }
        )
    storage.close()
    store = AnalyticsStore(db_path=db_path)
    yield store
    store.close()


class TestPerAppTimeSeries:
    def test_returns_empty_when_no_sessions_in_range(self, multi_day_sessions):
        result = multi_day_sessions.per_app_time_series(0.0, 1.0, TimeGranularity.DAY)
        assert result == []

    def test_hourly_granularity(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.HOUR
        )
        buckets = {r["time_bucket"] for r in result}
        assert len(buckets) == 5

    def test_daily_granularity(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.DAY
        )
        buckets = {r["time_bucket"] for r in result}
        assert len(buckets) == 3

    def test_weekly_granularity(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.WEEK
        )
        buckets = {r["time_bucket"] for r in result}
        assert len(buckets) == 1

    def test_monthly_granularity(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.MONTH
        )
        buckets = {r["time_bucket"] for r in result}
        assert len(buckets) == 1

    def test_ordering_within_bucket_by_desc_duration(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.DAY
        )
        day3_bucket = [r for r in result if "2026-01-07" in r["time_bucket"]]
        assert len(day3_bucket) == 2
        assert day3_bucket[0]["app_key"] == "Terminal.exe"
        assert day3_bucket[0]["total_duration_s"] == 100.0
        assert day3_bucket[1]["app_key"] == "Code.exe"
        assert day3_bucket[1]["total_duration_s"] == 50.0

    def test_ordering_across_buckets_asc(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        day3 = day1 + timedelta(days=2)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day3 + timedelta(days=1)).timestamp(), TimeGranularity.DAY
        )
        buckets = []
        for r in result:
            if r["time_bucket"] not in buckets:
                buckets.append(r["time_bucket"])
        assert buckets == sorted(buckets)

    def test_time_bucket_format_is_iso(self, multi_day_sessions):
        day1 = datetime(2026, 1, 5, tzinfo=timezone.utc)
        result = multi_day_sessions.per_app_time_series(
            day1.timestamp(), (day1 + timedelta(days=1)).timestamp(), TimeGranularity.DAY
        )
        assert result[0]["time_bucket"] == "2026-01-05T00:00:00"


class TestPerAppDuration:
    def test_returns_empty_when_no_sessions_in_range(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(0.0, 1.0)
        assert result == []

    def test_single_app_total(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(0.0, 3000.0)
        code = [r for r in result if r["app_key"] == "Code.exe"]
        assert len(code) == 1
        assert code[0]["total_duration_s"] == 350.0

    def test_multiple_apps_ordered_by_desc_duration(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(0.0, 3000.0)
        assert len(result) == 2
        assert result[0]["app_key"] == "Code.exe"
        assert result[0]["total_duration_s"] == 350.0
        assert result[1]["app_key"] == "Terminal.exe"
        assert result[1]["total_duration_s"] == 300.0

    def test_respects_time_range_lower_bound(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(1300.0, 3000.0)
        code = [r for r in result if r["app_key"] == "Code.exe"]
        assert len(code) == 1
        assert code[0]["total_duration_s"] == 50.0

    def test_respects_time_range_upper_bound(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(0.0, 1300.0)
        code = [r for r in result if r["app_key"] == "Code.exe"]
        assert len(code) == 1
        assert code[0]["total_duration_s"] == 300.0

    def test_includes_boundary_timestamps(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(1000.0, 1500.0)
        code = [r for r in result if r["app_key"] == "Code.exe"]
        assert len(code) == 1
        assert code[0]["total_duration_s"] == 300.0

    def test_returns_float_total(self, store_with_sessions):
        result = store_with_sessions.per_app_duration(0.0, 3000.0)
        assert isinstance(result[0]["total_duration_s"], float)

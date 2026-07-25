from datetime import datetime, timezone

T0 = datetime(2026, 7, 19, tzinfo=timezone.utc)


class TestWriteEvent:
    def test_writes_event_to_raw_events(self, in_memory_db, make_tick):
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=T0.timestamp(),
            payload={"app": "Code.exe"},
            source="foreground",
        )
        rows = in_memory_db._conn.execute("SELECT * FROM raw_events").fetchall()
        assert len(rows) == 1
        assert rows[0][3] == "foreground_transition"

    def test_get_raw_events_returns_event(self, in_memory_db, make_tick):
        ts = T0.timestamp()
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=ts,
            payload={"app": "Code.exe"},
            source="foreground",
        )
        results = in_memory_db.get_raw_events()
        assert len(results) == 1
        assert results[0]["event_type"] == "foreground_transition"
        assert results[0]["payload"]["app"] == "Code.exe"

    def test_get_raw_events_filtered(self, in_memory_db):
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1000.0,
            payload={},
            source="fg",
        )
        in_memory_db.write_event(
            event_type="power_change",
            timestamp=1100.0,
            payload={},
            source="pwr",
        )
        fg_events = in_memory_db.get_raw_events(event_type="foreground_transition")
        assert len(fg_events) == 1
        assert fg_events[0]["event_type"] == "foreground_transition"

    def test_get_raw_events_since_until(self, in_memory_db):
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1000.0,
            payload={},
            source="fg",
        )
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1100.0,
            payload={},
            source="fg",
        )
        results = in_memory_db.get_raw_events(since=1050.0, until=1150.0)
        assert len(results) == 1
        assert results[0]["timestamp"] == 1100.0

    def test_get_raw_events_desc(self, in_memory_db):
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1000.0,
            payload={},
            source="fg",
        )
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1100.0,
            payload={},
            source="fg",
        )
        results = in_memory_db.get_raw_events(desc=True)
        assert results[0]["timestamp"] > results[1]["timestamp"]

    def test_get_raw_events_limit(self, in_memory_db):
        for i in range(10):
            in_memory_db.write_event(
                event_type="foreground_transition",
                timestamp=float(1000 + i),
                payload={},
                source="fg",
            )
        results = in_memory_db.get_raw_events(limit=3)
        assert len(results) == 3

    def test_clear_all_data_clears_raw_events(self, in_memory_db):
        in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=1000.0,
            payload={},
            source="fg",
        )
        in_memory_db.clear_all_data()
        assert len(in_memory_db.get_raw_events()) == 0

    def test_clear_all_data_clears_sessions(self, in_memory_db):
        in_memory_db.write_canonical_session(
            {
                "device_id": "test",
                "platform": "windows",
                "start_ts": 1000.0,
                "end_ts": 1100.0,
                "duration_s": 100.0,
                "app_key": "Code.exe",
                "payload": {},
                "session_type": "foreground",
            }
        )
        in_memory_db.clear_all_data()
        assert len(in_memory_db.get_canonical_sessions()) == 0


class TestCanonicalSessions:
    def test_write_and_read_session(self, in_memory_db):
        in_memory_db.write_canonical_session(
            {
                "device_id": "test",
                "platform": "windows",
                "start_ts": 1000.0,
                "end_ts": 1100.0,
                "duration_s": 100.0,
                "app_key": "Code.exe",
                "payload": {"title": "main.py"},
                "session_type": "foreground",
            }
        )
        results = in_memory_db.get_canonical_sessions()
        assert len(results) == 1
        assert results[0]["app_key"] == "Code.exe"
        assert results[0]["payload"]["title"] == "main.py"

    def test_get_canonical_sessions_filtered(self, in_memory_db):
        for app in ["Code.exe", "brave.exe"]:
            in_memory_db.write_canonical_session(
                {
                    "device_id": "test",
                    "platform": "windows",
                    "start_ts": 1000.0,
                    "end_ts": 1100.0,
                    "duration_s": 100.0,
                    "app_key": app,
                    "payload": {},
                    "session_type": "foreground",
                }
            )
        results = in_memory_db.get_canonical_sessions(app_key="Code.exe")
        assert len(results) == 1


class TestUrlVisits:
    def test_write_and_get_url_visit(self, in_memory_db):
        import time
        seen_at = time.time()
        visit_id = in_memory_db.write_url_visit(
            url="https://github.com/user/repo",
            seen_at=seen_at,
            extraction_method="uia",
            confidence="high",
            scheme="https",
            host="github.com",
            domain="github.com",
            path="/user/repo",
            is_trackable=True,
        )
        assert visit_id > 0

        visits = in_memory_db.get_url_visits()
        assert len(visits) == 1
        v = visits[0]
        assert v["url"] == "https://github.com/user/repo"
        assert v["host"] == "github.com"
        assert v["domain"] == "github.com"
        assert v["extraction_method"] == "uia"
        assert v["confidence"] == "high"
        assert v["is_trackable"] is True

    def test_get_url_visits_filtered_by_device(self, in_memory_db):
        import time
        in_memory_db.write_url_visit(url="https://a.com", seen_at=time.time())
        result = in_memory_db.get_url_visits(device_id="nonexistent")
        assert len(result) == 0

    def test_get_url_visits_filtered_by_time(self, in_memory_db):
        in_memory_db.write_url_visit(url="https://a.com", seen_at=1000.0)
        in_memory_db.write_url_visit(url="https://b.com", seen_at=1100.0)

        results = in_memory_db.get_url_visits(since=1050.0, until=1150.0)
        assert len(results) == 1
        assert results[0]["url"] == "https://b.com"

    def test_get_url_visits_limit(self, in_memory_db):
        import time
        for i in range(5):
            in_memory_db.write_url_visit(url=f"https://x.com/{i}", seen_at=time.time())
        results = in_memory_db.get_url_visits(limit=2)
        assert len(results) == 2

    def test_clear_all_data_clears_url_visits(self, in_memory_db):
        import time
        in_memory_db.write_url_visit(url="https://a.com", seen_at=time.time())
        in_memory_db.clear_all_data()
        assert len(in_memory_db.get_url_visits()) == 0

    def test_backfill_event_id(self, in_memory_db, make_tick):
        import time
        visit_id = in_memory_db.write_url_visit(url="https://a.com", seen_at=time.time())
        event_id = in_memory_db.write_event(
            event_type="foreground_transition",
            timestamp=time.time(),
            payload={"app": "brave.exe"},
            source="foreground",
        )
        in_memory_db.backfill_url_event_id(visit_id, event_id)
        visits = in_memory_db.get_url_visits()
        assert visits[0]["event_id"] == event_id

    def test_backfill_session_id(self, in_memory_db):
        import time
        visit_id = in_memory_db.write_url_visit(url="https://a.com", seen_at=time.time())
        sess_id = in_memory_db.write_canonical_session({
            "device_id": "test",
            "platform": "windows",
            "start_ts": 1000.0,
            "end_ts": 1100.0,
            "duration_s": 100.0,
            "app_key": "brave.exe",
            "payload": {},
            "session_type": "foreground",
        })
        in_memory_db.backfill_url_session_id(visit_id, sess_id)
        visits = in_memory_db.get_url_visits()
        assert visits[0]["session_id"] == sess_id


class TestSchemaMigration:
    def test_migration_sets_version(self, tmp_path, make_tick):
        from core.storage import Storage

        db = str(tmp_path / "test.db")
        storage = Storage(db_path=db)
        assert storage._conn.execute("PRAGMA user_version").fetchone()[0] == 7
        storage.close()

    def test_migration_skipped_when_up_to_date(self, tmp_path, make_tick):
        from core.storage import Storage

        db = str(tmp_path / "test.db")
        storage1 = Storage(db_path=db)
        assert storage1._conn.execute("PRAGMA user_version").fetchone()[0] == 7

        storage1.write_event(
            event_type="foreground_transition",
            timestamp=1000.0,
            payload={"app": "Code.exe"},
            source="foreground",
        )
        assert len(storage1.get_raw_events()) == 1
        storage1.close()

        storage2 = Storage(db_path=db)
        assert storage2._conn.execute("PRAGMA user_version").fetchone()[0] == 7
        events = storage2.get_raw_events()
        assert len(events) == 1
        assert events[0]["payload"]["app"] == "Code.exe"
        storage2.close()

    def test_migration_is_idempotent(self, tmp_path, make_tick):
        from core.storage import Storage

        db = str(tmp_path / "test.db")
        for i in range(5):
            storage = Storage(db_path=db)
            assert storage._conn.execute("PRAGMA user_version").fetchone()[0] == 7
            if i == 0:
                storage.write_event(
                    event_type="foreground_transition",
                    timestamp=1000.0,
                    payload={"app": "Code.exe"},
                    source="foreground",
                )
            storage.close()

        final = Storage(db_path=db)
        events = final.get_raw_events()
        assert len(events) == 1
        final.close()

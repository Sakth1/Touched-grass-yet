import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest

T0 = datetime(2026, 7, 19, 0, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def tmp_db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


class TestPulseMerge:
    def test_same_data_extends_duration(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        t2 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0.replace(second=1))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 1
        assert events[0]["duration"] == 1.0
        assert events[0]["data"] == {"app": "Code.exe"}

    def test_different_data_creates_new_row(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        t2 = make_tick(watcher="foreground", data={"app": "Terminal.exe"}, timestamp=T0.replace(second=1))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 2
        assert events[0]["data"]["app"] == "Code.exe"
        assert events[1]["data"]["app"] == "Terminal.exe"

    def test_merge_at_exact_pulsetime_boundary(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        t2 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0.replace(second=3))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 1
        assert events[0]["duration"] == 3.0

    def test_past_pulsetime_creates_new_row(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        t2 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0.replace(second=4))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 2
        assert events[0]["duration"] == 0.0
        assert events[1]["duration"] == 0.0

    def test_merge_afk_by_status_only(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="afk", data={"status": "active", "idle_seconds": 10.0}, timestamp=T0)
        t2 = make_tick(watcher="afk", data={"status": "active", "idle_seconds": 12.0}, timestamp=T0.replace(second=5))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 1
        assert events[0]["duration"] == 5.0

    def test_afk_status_change_creates_new_row(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="afk", data={"status": "active", "idle_seconds": 10.0}, timestamp=T0)
        t2 = make_tick(watcher="afk", data={"status": "idle", "idle_seconds": 65.0}, timestamp=T0.replace(second=5))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        events = in_memory_db.get_events()
        assert len(events) == 2
        assert events[0]["data"]["status"] == "active"
        assert events[1]["data"]["status"] == "idle"


class TestMultiWatcher:
    def test_different_watchers_dont_interfere(self, in_memory_db, make_tick):
        t1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        t2 = make_tick(watcher="afk", data={"status": "active"}, timestamp=T0.replace(second=1))
        t3 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0.replace(second=2))
        in_memory_db.on_tick(t1)
        in_memory_db.on_tick(t2)
        in_memory_db.on_tick(t3)
        events = in_memory_db.get_events()
        assert len(events) == 2
        fg_events = [e for e in events if e["watcher"] == "foreground"]
        afk_events = [e for e in events if e["watcher"] == "afk"]
        assert len(fg_events) == 1
        assert len(afk_events) == 1
        assert fg_events[0]["duration"] == 2.0

    def test_watchers_maintain_independent_merge_state(self, in_memory_db, make_tick):
        fg1 = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        afk1 = make_tick(watcher="afk", data={"status": "active"}, timestamp=T0.replace(second=1))
        pwr1 = make_tick(watcher="power", data={"battery_pct": 85, "charging": True}, timestamp=T0.replace(second=2))
        fg2 = make_tick(watcher="foreground", data={"app": "Terminal.exe"}, timestamp=T0.replace(second=3))
        in_memory_db.on_tick(fg1)
        in_memory_db.on_tick(afk1)
        in_memory_db.on_tick(pwr1)
        in_memory_db.on_tick(fg2)
        events = in_memory_db.get_events()
        assert len(events) == 4


class TestSchemaMigration:
    def test_migration_preserves_existing_data(self, tmp_db_path):
        conn = sqlite3.connect(tmp_db_path, isolation_level=None)
        conn.execute("CREATE TABLE custom_data (id INTEGER PRIMARY KEY, name TEXT)")
        conn.execute("INSERT INTO custom_data VALUES (1, 'survived')")
        conn.execute("PRAGMA user_version = 0")
        conn.close()

        from core.storage import Storage

        storage = Storage(db_path=tmp_db_path)

        tables = storage._conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        table_names = [r[0] for r in tables]
        assert "devices" in table_names
        assert any(t.startswith("events_") for t in table_names)
        assert "custom_data" in table_names

        row = storage._conn.execute("SELECT name FROM custom_data WHERE id=1").fetchone()
        assert row[0] == "survived"
        storage.close()

    def test_migration_skipped_when_up_to_date(self, tmp_db_path, make_tick):
        from core.storage import Storage

        storage1 = Storage(db_path=tmp_db_path)
        assert storage1._conn.execute("PRAGMA user_version").fetchone()[0] == 2

        tick = make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0)
        storage1.on_tick(tick)
        assert len(storage1.get_events()) == 1
        storage1.close()

        storage2 = Storage(db_path=tmp_db_path)
        assert storage2._conn.execute("PRAGMA user_version").fetchone()[0] == 2
        events = storage2.get_events()
        assert len(events) == 1
        assert events[0]["data"]["app"] == "Code.exe"
        storage2.close()

    def test_migration_is_idempotent(self, tmp_db_path, make_tick):
        from core.storage import Storage

        for i in range(5):
            storage = Storage(db_path=tmp_db_path)
            assert storage._conn.execute("PRAGMA user_version").fetchone()[0] == 2
            if i == 0:
                storage.on_tick(make_tick(watcher="foreground", data={"app": "Code.exe"}, timestamp=T0))
            storage.close()

        final = Storage(db_path=tmp_db_path)
        events = final.get_events()
        assert len(events) == 1
        final.close()

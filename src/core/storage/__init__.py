import json
import logging
import os
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.device_identity import get_device_id
from core.paths import get_data_dir

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 5


def _db_path() -> str:
    return os.path.join(get_data_dir(), "data.db")


def _schema_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "schemas")


class Storage:
    _TEST_DEVICE_ID = "00000000-0000-0000-0000-000000000001"

    def __init__(self, db_path: str | None = None):
        self._device_id = get_device_id()
        self._short_id = self._device_id[:8]
        self._platform = platform.system().lower()

        path = db_path or _db_path()
        if self._device_id == self._TEST_DEVICE_ID and path != ":memory:":
            logger.warning("Test device ID used with file-based DB at %s — this may contaminate production data", path)

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")

        self._run_migrations()
        self._register_device()

    def _run_migrations(self) -> None:
        cursor = self._conn.execute("PRAGMA user_version")
        current_version = cursor.fetchall()[0][0] or 0

        if current_version < SCHEMA_VERSION:
            logger.info("Migrating schema v%d -> v%d", current_version, SCHEMA_VERSION)

            core_sql = Path(_schema_dir(), "core.sql").read_text()
            for stmt in core_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)

            platform_sql = Path(_schema_dir(), f"{self._platform}.sql").read_text()
            platform_sql = platform_sql.replace("{short_id}", self._short_id)
            for stmt in platform_sql.split(";"):
                stmt = stmt.strip()
                if stmt:
                    self._conn.execute(stmt)

            self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            logger.info("Schema migration complete")

    def _register_device(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT OR IGNORE INTO devices
               (device_id, hostname, platform, first_seen, is_current)
               VALUES (?, ?, ?, ?, 1)""",
            (self._device_id, platform.node(), self._platform, now),
        )
        self._conn.execute(
            "UPDATE devices SET last_seen = ? WHERE device_id = ?",
            (now, self._device_id),
        )

    def write_event(
        self,
        event_type: str,
        timestamp: float,
        payload: dict,
        source: str,
    ) -> int:
        self._conn.execute(
            """INSERT INTO raw_events
               (device_id, platform, event_type, timestamp, collected_at, payload, source)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                self._device_id,
                self._platform,
                event_type,
                timestamp,
                datetime.now(timezone.utc).timestamp(),
                json.dumps(payload),
                source,
            ),
        )
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_raw_events(
        self,
        event_type: str | None = None,
        source: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int | None = None,
        desc: bool = False,
    ) -> list[dict]:
        filters: list[str] = []
        params: list = []

        if event_type:
            filters.append("event_type = ?")
            params.append(event_type)
        if source:
            filters.append("source = ?")
            params.append(source)
        if since is not None:
            filters.append("timestamp >= ?")
            params.append(since)
        if until is not None:
            filters.append("timestamp <= ?")
            params.append(until)

        sql = "SELECT id, device_id, platform, event_type, timestamp, collected_at, payload, source FROM raw_events"
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY timestamp DESC" if desc else " ORDER BY timestamp ASC"
        if limit is not None:
            sql += f" LIMIT {limit}"

        return [
            {
                "id": r[0],
                "device_id": r[1],
                "platform": r[2],
                "event_type": r[3],
                "timestamp": r[4],
                "collected_at": r[5],
                "payload": json.loads(r[6]),
                "source": r[7],
            }
            for r in self._conn.execute(sql, params).fetchall()
        ]

    def write_canonical_session(self, session: dict) -> int:
        self._conn.execute(
            """INSERT INTO sessions
               (device_id, platform, start_ts, end_ts, duration_s, app_key, payload, session_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session["device_id"],
                session["platform"],
                session["start_ts"],
                session.get("end_ts"),
                session.get("duration_s"),
                session["app_key"],
                json.dumps(session["payload"]),
                session.get("session_type", "foreground"),
            ),
        )
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_canonical_sessions(
        self,
        app_key: str | None = None,
        device_id: str | None = None,
        since: float | None = None,
        until: float | None = None,
        platform: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        filters: list[str] = []
        params: list = []

        if app_key:
            filters.append("app_key = ?")
            params.append(app_key)
        if device_id:
            filters.append("device_id = ?")
            params.append(device_id)
        if since is not None:
            filters.append("start_ts >= ?")
            params.append(since)
        if until is not None:
            filters.append("COALESCE(end_ts, start_ts) <= ?")
            params.append(until)
        if platform:
            filters.append("platform = ?")
            params.append(platform)

        sql = (
            "SELECT id, device_id, platform, start_ts, end_ts, duration_s, app_key, payload, session_type FROM sessions"
        )
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY start_ts ASC"
        if limit is not None:
            sql += f" LIMIT {limit}"

        return [
            {
                "id": r[0],
                "device_id": r[1],
                "platform": r[2],
                "start_ts": r[3],
                "end_ts": r[4],
                "duration_s": r[5],
                "app_key": r[6],
                "payload": json.loads(r[7]),
                "session_type": r[8],
            }
            for r in self._conn.execute(sql, params).fetchall()
        ]

    def clear_all_data(self) -> None:
        self._conn.execute("DELETE FROM raw_events")
        self._conn.execute("DELETE FROM sessions")
        for suffix in ("events_", "observations_", "sessions_"):
            legacy = f"{suffix}{self._short_id}"
            self._conn.execute(f"DROP TABLE IF EXISTS {legacy}")
        self._conn.execute(
            "UPDATE devices SET first_seen = ? WHERE device_id = ?",
            (datetime.now(timezone.utc).isoformat(), self._device_id),
        )
        self._conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._conn.execute("VACUUM")
        logger.warning("All data cleared for device %s", self._short_id)

    def close(self) -> None:
        self._conn.close()

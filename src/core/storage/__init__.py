import json
import logging
import os
import platform
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.device_identity import get_device_id
from core.paths import get_data_dir
from utils.models import Observation, Tick

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

MERGE_CONFIG: dict[str, dict] = {
    "android_foreground": {
        "merge_keys": None,
        "pulsetime": 60.0,
    },
    "android_afk": {
        "merge_keys": ["status"],
        "pulsetime": 10.0,
    },
    "android_power": {
        "merge_keys": None,
        "pulsetime": 120.0,
    },
    "foreground": {
        "merge_keys": None,
        "pulsetime": 3.0,
    },
    "afk": {
        "merge_keys": ["status"],
        "pulsetime": 10.0,
    },
    "power": {
        "merge_keys": None,
        "pulsetime": 120.0,
    },
}


def _db_path() -> str:
    return os.path.join(get_data_dir(), "data.db")


def _schema_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "schemas")


def _epoch(dt: datetime) -> float:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


class Storage:
    _TEST_DEVICE_ID = "00000000-0000-0000-0000-000000000001"

    def __init__(self, db_path: str | None = None):
        self._device_id = get_device_id()
        self._short_id = self._device_id[:8]
        self._platform = platform.system().lower()

        path = db_path or _db_path()
        if self._device_id == self._TEST_DEVICE_ID and path != ":memory:":
            logger.warning(
                "Test device ID used with file-based DB at %s — "
                "this may contaminate production data", path
            )

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

    def _table_name(self) -> str:
        return f"events_{self._short_id}"

    def _data_matches(self, tick: Tick, last_data: str | None) -> bool:
        if last_data is None:
            return False
        cfg = MERGE_CONFIG.get(tick.watcher, {"merge_keys": None})
        keys = cfg["merge_keys"]
        last = json.loads(last_data)
        if keys is None:
            return tick.data == last
        return all(tick.data.get(k) == last.get(k) for k in keys)

    def on_tick(self, tick: Tick) -> None:
        try:
            ts = _epoch(tick.timestamp)

            last = self._conn.execute(
                f"""SELECT id, timestamp, duration, data
                    FROM {self._table_name()}
                    WHERE watcher = ? ORDER BY timestamp DESC LIMIT 1""",
                (tick.watcher,),
            ).fetchall()

            if last:
                last_id, last_ts, last_dur, last_data = last[0]
                if self._data_matches(tick, last_data):
                    pulse_end = last_ts + last_dur + MERGE_CONFIG.get(
                        tick.watcher, {}
                    ).get("pulsetime", 3.0)
                    if ts <= pulse_end:
                        new_dur = round(max(last_dur, ts - last_ts), 2)
                        self._conn.execute(
                            f"UPDATE {self._table_name()} SET duration = ? WHERE id = ?",
                            (new_dur, last_id),
                        )
                        return

            self._conn.execute(
                f"""INSERT INTO {self._table_name()}
                    (watcher, timestamp, duration, data)
                    VALUES (?, ?, ?, ?)""",
                (tick.watcher, ts, 0.0, json.dumps(tick.data)),
            )
        except Exception:
            logger.exception("Storage write failed for watcher %s", tick.watcher)

    def get_events(
        self,
        watcher: str | None = None,
        since: float | None = None,
        until: float | None = None,
        device_id: str | None = None,
        limit: int | None = None,
        desc: bool = False,
    ) -> list[dict]:
        tbl = f"events_{device_id[:8]}" if device_id else self._table_name()
        filters = []
        params = []

        if watcher:
            filters.append("watcher = ?")
            params.append(watcher)
        if since is not None:
            filters.append("timestamp >= ?")
            params.append(since)
        if until is not None:
            filters.append("timestamp <= ?")
            params.append(until)

        sql = f"SELECT id, watcher, timestamp, duration, data FROM {tbl}"
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY timestamp DESC" if desc else " ORDER BY timestamp ASC"
        if limit is not None:
            sql += f" LIMIT {limit}"

        return [
            {
                "id": r[0],
                "watcher": r[1],
                "timestamp": r[2],
                "duration": r[3],
                "data": json.loads(r[4]),
            }
            for r in self._conn.execute(sql, params).fetchall()
        ]

    def _observations_table(self) -> str:
        return f"observations_{self._short_id}"

    def _sessions_table(self) -> str:
        return f"sessions_{self._short_id}"

    def on_observation(self, obs: Observation) -> None:
        try:
            ts = _epoch(obs.timestamp)
            self._conn.execute(
                f"""INSERT INTO {self._observations_table()}
                    (watcher, timestamp, data, obs_type)
                    VALUES (?, ?, ?, ?)""",
                (obs.watcher, ts, json.dumps(obs.data), obs.observation_type),
            )
        except Exception:
            logger.exception("Storage write failed for watcher %s", obs.watcher)

    def get_observations(
        self,
        watcher: str | None = None,
        since: float | None = None,
        until: float | None = None,
        limit: int | None = None,
        desc: bool = False,
    ) -> list[dict]:
        tbl = self._observations_table()
        filters: list[str] = []
        params: list = []

        if watcher:
            filters.append("watcher = ?")
            params.append(watcher)
        if since is not None:
            filters.append("timestamp >= ?")
            params.append(since)
        if until is not None:
            filters.append("timestamp <= ?")
            params.append(until)

        sql = f"SELECT id, watcher, timestamp, data, obs_type FROM {tbl}"
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY timestamp DESC" if desc else " ORDER BY timestamp ASC"
        if limit is not None:
            sql += f" LIMIT {limit}"

        return [
            {
                "id": r[0],
                "watcher": r[1],
                "timestamp": r[2],
                "data": json.loads(r[3]),
                "obs_type": r[4],
            }
            for r in self._conn.execute(sql, params).fetchall()
        ]

    def get_sessions(
        self,
        watcher: str | None = None,
        since: float | None = None,
        until: float | None = None,
        app_key: str | None = None,
        limit: int | None = None,
    ) -> list[dict]:
        tbl = self._sessions_table()
        filters: list[str] = []
        params: list = []

        if watcher:
            filters.append("watcher = ?")
            params.append(watcher)
        if since is not None:
            filters.append("start_ts >= ?")
            params.append(since)
        if until is not None:
            filters.append("COALESCE(end_ts, start_ts) <= ?")
            params.append(until)
        if app_key:
            filters.append("app_key = ?")
            params.append(app_key)

        sql = f"SELECT id, watcher, start_ts, end_ts, duration_s, app_key, data, source FROM {tbl}"
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY start_ts ASC"
        if limit is not None:
            sql += f" LIMIT {limit}"

        return [
            {
                "id": r[0],
                "watcher": r[1],
                "start_ts": r[2],
                "end_ts": r[3],
                "duration_s": r[4],
                "app_key": r[5],
                "data": json.loads(r[6]),
                "source": r[7],
            }
            for r in self._conn.execute(sql, params).fetchall()
        ]

    def write_session(self, session: dict) -> int:
        self._conn.execute(
            f"""INSERT INTO {self._sessions_table()}
                (watcher, start_ts, end_ts, duration_s, app_key, data, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                session["watcher"],
                session["start_ts"],
                session.get("end_ts"),
                session.get("duration_s"),
                session["app_key"],
                json.dumps(session["data"]),
                session.get("source"),
            ),
        )
        return self._conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def update_session_end(self, session_id: int, end_ts: float, duration_s: float) -> None:
        self._conn.execute(
            f"UPDATE {self._sessions_table()} SET end_ts = ?, duration_s = ? WHERE id = ?",
            (end_ts, duration_s, session_id),
        )

    def close(self) -> None:
        self._conn.close()

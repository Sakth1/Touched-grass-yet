import logging
import os
from enum import Enum

import duckdb

from core.paths import get_data_dir

logger = logging.getLogger(__name__)


class TimeGranularity(Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


_SYNC_TABLES = ["raw_events", "sessions", "url_visits"]


def _db_path() -> str:
    return os.path.join(get_data_dir(), "data.db")


def _analytics_db_path() -> str:
    return os.path.join(get_data_dir(), "analytics.db")


class AnalyticsStore:
    def __init__(self, db_path: str | None = None, analytics_db_path: str | None = None):
        path = db_path or _db_path()
        adb_path = analytics_db_path or os.path.join(os.path.dirname(path), "analytics.db")

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._path = path
        self._analytics_db_path = adb_path
        self._conn = duckdb.connect(adb_path)
        self._conn.execute(f"ATTACH IF NOT EXISTS '{path}' AS data (TYPE SQLITE)")
        self._ensure_schema()
        logger.info("AnalyticsStore initialised (sqlite=%s, duckdb=%s)", path, adb_path)

    # ------------------------------------------------------------------ #
    #  Schema
    # ------------------------------------------------------------------ #

    def _ensure_schema(self) -> None:
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS _sync_metadata (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        for table in _SYNC_TABLES:
            self._conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {table} AS
                SELECT * FROM data.{table} WHERE 1=0
            """)

    # ------------------------------------------------------------------ #
    #  Sync
    # ------------------------------------------------------------------ #

    def sync_from_sqlite(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for table in _SYNC_TABLES:
            try:
                result[table] = self._sync_table(table)
            except Exception:
                logger.exception("Sync failed for table %s", table)
                result[table] = -1
        return result

    def _sync_table(self, table: str) -> int:
        last_id = self._get_meta(f"last_synced_{table}_id", 0)
        self._conn.execute(
            f"INSERT INTO {table} SELECT * FROM data.{table} WHERE id > ?",
            [last_id],
        )
        max_id = self._conn.execute(
            f"SELECT COALESCE(MAX(id), 0) FROM {table}"
        ).fetchone()[0]
        self._set_meta(f"last_synced_{table}_id", max_id)
        synced = max_id - last_id
        if synced > 0:
            logger.info("Synced %d rows to %s (last_id %d -> %d)", synced, table, last_id, max_id)
        return synced

    # ------------------------------------------------------------------ #
    #  Clear
    # ------------------------------------------------------------------ #

    def clear(self) -> None:
        for table in _SYNC_TABLES:
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.execute("DELETE FROM _sync_metadata")
        logger.info("AnalyticsStore cleared")

    # ------------------------------------------------------------------ #
    #  Metadata helpers
    # ------------------------------------------------------------------ #

    def _get_meta(self, key: str, default: int = 0) -> int:
        row = self._conn.execute(
            "SELECT value FROM _sync_metadata WHERE key = ?", [key]
        ).fetchone()
        return int(row[0]) if row else default

    def _set_meta(self, key: str, value: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO _sync_metadata (key, value) VALUES (?, ?)",
            [key, str(value)],
        )

    # ------------------------------------------------------------------ #
    #  Queries (still via attached SQLite)
    # ------------------------------------------------------------------ #

    def per_app_duration(self, date_from: float, date_to: float) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT app_key, SUM(duration_s) AS total_duration_s
            FROM data.sessions
            WHERE duration_s IS NOT NULL
              AND start_ts >= ?
              AND start_ts <= ?
            GROUP BY app_key
            ORDER BY total_duration_s DESC
            """,
            [date_from, date_to],
        ).fetchall()
        return [
            {"app_key": r[0], "total_duration_s": r[1]}
            for r in rows
        ]

    def per_app_time_series(
        self,
        date_from: float,
        date_to: float,
        granularity: TimeGranularity = TimeGranularity.DAY,
    ) -> list[dict]:
        rows = self._conn.execute(
            f"""
            SELECT
                strftime(date_trunc('{granularity.value}', to_timestamp(start_ts)), '%Y-%m-%dT%H:%M:%S') AS time_bucket,
                app_key,
                SUM(duration_s) AS total_duration_s
            FROM data.sessions
            WHERE duration_s IS NOT NULL
              AND start_ts >= ?
              AND start_ts <= ?
            GROUP BY time_bucket, app_key
            ORDER BY time_bucket ASC, total_duration_s DESC
            """,
            [date_from, date_to],
        ).fetchall()
        return [
            {"time_bucket": r[0], "app_key": r[1], "total_duration_s": r[2]}
            for r in rows
        ]

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

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


def _db_path() -> str:
    return os.path.join(get_data_dir(), "data.db")


class AnalyticsStore:
    def __init__(self, db_path: str | None = None):
        path = db_path or _db_path()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        self._conn = duckdb.connect(":memory:")
        self._path = path
        self._conn.execute(f"ATTACH '{path}' AS data (TYPE SQLITE)")
        logger.info("AnalyticsStore attached to %s", path)

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

import csv
import datetime
import json
import logging
from io import StringIO
from typing import Any

logger = logging.getLogger(__name__)


class ExportService:
    """Platform-agnostic export data preparation.

    Each ``prepare_*`` static method returns ``(filename, utf-8-encoded bytes)``.
    The caller is responsible for persisting the bytes to the desired location.

    Two output modes:
    - ``prepare_events`` / ``prepare_json``: legacy pulse-merge rows with duration
    - ``prepare_observations``: raw observations (no duration field)
    - ``prepare_sessions``: computed foreground sessions with computed duration
    """

    @staticmethod
    def prepare_csv(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = _make_filename(ext="csv")
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "watcher", "timestamp", "duration", "data"])
        for r in rows:
            w.writerow([
                r["id"],
                r["watcher"],
                _fmt_timestamp(r["timestamp"]),
                r["duration"],
                json.dumps(r["data"], ensure_ascii=False),
            ])
        return filename, buf.getvalue().encode("utf-8")

    @staticmethod
    def prepare_json(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = _make_filename(ext="json")
        out = [
            {
                "id": r["id"],
                "watcher": r["watcher"],
                "timestamp": _fmt_timestamp(r["timestamp"]),
                "duration": r["duration"],
                "data": r["data"],
            }
            for r in rows
        ]
        data = json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8")
        return filename, data

    @staticmethod
    def prepare_observations(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = _make_filename("observations", "json")
        out = [
            {
                "id": r["id"],
                "watcher": r["watcher"],
                "timestamp": _fmt_timestamp(r["timestamp"]),
                "data": r["data"],
                "obs_type": r.get("obs_type", "snapshot"),
            }
            for r in rows
        ]
        data = json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8")
        return filename, data

    @staticmethod
    def prepare_sessions(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = _make_filename("sessions", "json")
        out = [
            {
                "id": r.get("id"),
                "watcher": r["watcher"],
                "start_ts": _fmt_timestamp(r["start_ts"]),
                "end_ts": _fmt_timestamp(r["end_ts"]) if r.get("end_ts") else None,
                "duration_s": r.get("duration_s"),
                "app_key": r["app_key"],
                "data": r["data"],
                "source": r.get("source"),
            }
            for r in rows
        ]
        data = json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8")
        return filename, data


def _make_filename(prefix: str = "events", ext: str = "json") -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}.{ext}"


def _fmt_timestamp(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

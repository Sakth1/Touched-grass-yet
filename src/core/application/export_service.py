import csv
import json
import logging
from io import StringIO
from typing import Any

from utils.files import timestamped_filename
from utils.time_utils import fmt_timestamp

logger = logging.getLogger(__name__)


class ExportService:
    """Platform-agnostic export data preparation.

    Each ``prepare_*`` static method returns ``(filename, utf-8-encoded bytes)``.
    The caller is responsible for persisting the bytes to the desired location.
    """

    @staticmethod
    def prepare_raw_events_csv(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = timestamped_filename("raw_events", "csv")
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(
            ["id", "event_type", "timestamp", "collected_at", "source", "payload"]
        )
        for r in rows:
            w.writerow(
                [
                    r["id"],
                    r["event_type"],
                    fmt_timestamp(r["timestamp"]),
                    fmt_timestamp(r["collected_at"]),
                    r["source"],
                    json.dumps(r["payload"], ensure_ascii=False),
                ]
            )
        return filename, buf.getvalue().encode("utf-8")

    @staticmethod
    def prepare_raw_events(rows: list[dict[str, Any]]) -> tuple[str, bytes]:
        filename = timestamped_filename("raw_events", "json")
        out = [
            {
                "id": r["id"],
                "device_id": r["device_id"],
                "platform": r["platform"],
                "event_type": r["event_type"],
                "timestamp": fmt_timestamp(r["timestamp"]),
                "collected_at": fmt_timestamp(r["collected_at"]),
                "payload": r["payload"],
                "source": r["source"],
            }
            for r in rows
        ]
        data = json.dumps(out, indent=2, ensure_ascii=False).encode("utf-8")
        return filename, data

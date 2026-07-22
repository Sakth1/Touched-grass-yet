import csv
import json
from io import StringIO

from core.application.export_service import ExportService


class TestPrepareCsv:
    def test_empty_rows(self):
        filename, data = ExportService.prepare_csv([])
        assert filename.endswith(".csv")
        decoded = data.decode("utf-8")
        reader = csv.reader(StringIO(decoded))
        rows = list(reader)
        assert rows[0] == ["id", "watcher", "timestamp", "duration", "data"]
        assert len(rows) == 1

    def test_single_row(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 60, "data": {"key": "val"}},
        ]
        filename, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        reader = csv.reader(StringIO(decoded))
        rows_out = list(reader)
        assert len(rows_out) == 2
        assert rows_out[1][0] == "1"
        assert rows_out[1][1] == "test"
        assert "key" in rows_out[1][4]

    def test_multiple_rows(self):
        rows = [
            {"id": i, "watcher": "w", "timestamp": 1700000000.0 + i, "duration": i * 10, "data": {}}
            for i in range(5)
        ]
        filename, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        reader = csv.reader(StringIO(decoded))
        rows_out = list(reader)
        assert len(rows_out) == 6  # header + 5 rows

    def test_data_with_nested_dict(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 30,
             "data": {"level1": {"level2": "deep"}}},
        ]
        _, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        reader = csv.reader(StringIO(decoded))
        rows_out = list(reader)
        assert '"level2"' in rows_out[1][4]

    def test_filename_has_timestamp_format(self):
        filename, _ = ExportService.prepare_csv([])
        assert filename.count("_") >= 1
        assert filename.endswith(".csv")
        assert filename.startswith("events_")

    def test_unicode_in_data(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 0, "data": {"name": "José café ñoño"}},
        ]
        _, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        assert "José" in decoded

    def test_large_duration_zero(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 0, "data": {}},
        ]
        _, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        assert ",0," in decoded.replace('"', "")

    def test_data_list_field(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 1, "data": {"items": [1, 2, 3]}},
        ]
        _, data = ExportService.prepare_csv(rows)
        decoded = data.decode("utf-8")
        assert "[1, 2, 3]" in decoded


class TestPrepareJson:
    def test_empty_rows(self):
        filename, data = ExportService.prepare_json([])
        assert filename.endswith(".json")
        parsed = json.loads(data.decode("utf-8"))
        assert parsed == []

    def test_single_row(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 60, "data": {"key": "val"}},
        ]
        _, data = ExportService.prepare_json(rows)
        parsed = json.loads(data.decode("utf-8"))
        assert len(parsed) == 1
        assert parsed[0]["id"] == 1
        assert parsed[0]["data"]["key"] == "val"

    def test_timestamp_formatted(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 0, "data": {}},
        ]
        _, data = ExportService.prepare_json(rows)
        parsed = json.loads(data.decode("utf-8"))
        assert parsed[0]["timestamp"] == "2023-11-14 22:13:20"

    def test_unicode(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 0, "data": {"name": "José café"}},
        ]
        _, data = ExportService.prepare_json(rows)
        decoded = data.decode("utf-8")
        assert "José" in decoded

    def test_pretty_print(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 0, "data": {}},
        ]
        _, data = ExportService.prepare_json(rows)
        decoded = data.decode("utf-8")
        assert "\n  " in decoded  # indent=2 produces newlines with spaces

    def test_multiple_rows(self):
        rows = [
            {"id": i, "watcher": "w", "timestamp": 1700000000.0 + i, "duration": i, "data": {}}
            for i in range(100)
        ]
        _, data = ExportService.prepare_json(rows)
        parsed = json.loads(data.decode("utf-8"))
        assert len(parsed) == 100

    def test_filename_has_timestamp_format(self):
        filename, _ = ExportService.prepare_json([])
        assert filename.endswith(".json")
        assert filename.startswith("events_")


class TestConsistency:
    def test_csv_and_json_same_data(self):
        rows = [
            {"id": 1, "watcher": "test", "timestamp": 1700000000.0, "duration": 60, "data": {"key": "val"}},
            {"id": 2, "watcher": "test", "timestamp": 1700000100.0, "duration": 30, "data": {}},
        ]
        csv_fn, csv_data = ExportService.prepare_csv(rows)
        json_fn, json_data = ExportService.prepare_json(rows)
        assert csv_fn != json_fn
        assert len(csv_data) > 0
        assert len(json_data) > 0

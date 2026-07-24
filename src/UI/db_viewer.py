import datetime
import logging
import os
import platform

import flet as ft

from core.application.collection_manager import CollectionManager
from core.application.export_service import ExportService
from core.paths import get_export_dir

logger = logging.getLogger(__name__)

_SOURCES = [
    "All",
    "foreground",
    "android_foreground",
    "android_app_usage",
    "afk",
    "android_afk",
    "power",
    "android_power",
]


class DbViewer:
    def __init__(self, page: ft.Page, manager: CollectionManager):
        self._page = page
        self._manager = manager
        self._status_text = ft.Text("", size=12, color=ft.Colors.GREY_400)
        self._watcher_dd = ft.Dropdown(
            width=140,
            height=48,
            text_size=13,
            label="Watcher",
            label_style=ft.TextStyle(size=11),
            options=[ft.dropdown.Option("All")],
            value="All",
        )
        self._limit_tf = ft.TextField(
            width=70,
            height=48,
            value="500",
            text_size=13,
            label="Max",
            label_style=ft.TextStyle(size=11),
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        self._rows_lv = ft.ListView(expand=True, auto_scroll=False, spacing=4, padding=4)
        self._file_picker = ft.FilePicker()
        self._build()

    def _build(self):
        self._view = ft.Container(
            visible=False,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BLACK),
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("DB Viewer (dev)", size=22, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                ft.Icons.CLOSE,
                                on_click=lambda e: self.hide(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=8),
                    ft.Row(
                        wrap=True,
                        controls=[
                            self._watcher_dd,
                            self._limit_tf,
                            ft.Button(
                                "Refresh",
                                icon=ft.Icons.REFRESH,
                                on_click=self._load_data,
                            ),
                            ft.Button(
                                "CSV",
                                icon=ft.Icons.FILE_DOWNLOAD,
                                on_click=self._export_csv,
                            ),
                            ft.Button(
                                "JSON",
                                icon=ft.Icons.FILE_DOWNLOAD_DONE,
                                on_click=self._export_json,
                            ),
                        ],
                        spacing=6,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    self._status_text,
                    ft.Container(
                        content=self._rows_lv,
                        border=ft.Border(
                            left=ft.BorderSide(1, ft.Colors.GREY_700),
                            top=ft.BorderSide(1, ft.Colors.GREY_700),
                            right=ft.BorderSide(1, ft.Colors.GREY_700),
                            bottom=ft.BorderSide(1, ft.Colors.GREY_700),
                        ),
                        border_radius=6,
                        padding=4,
                        expand=True,
                        bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.GREY_900),
                    ),
                ],
                expand=True,
                spacing=6,
            ),
        )

    def show(self):
        self._populate_watcher_filter()
        self._load_data()
        self._view.visible = True
        self._page.update()

    def hide(self):
        self._view.visible = False
        self._page.update()

    @property
    def overlay(self) -> ft.Container:
        return self._view

    def _populate_watcher_filter(self):
        current = self._watcher_dd.value
        self._watcher_dd.options = [ft.dropdown.Option(w) for w in _SOURCES]
        self._watcher_dd.value = current if current in _SOURCES else "All"

    def _load_data(self, e=None):
        try:
            watcher = self._watcher_dd.value
            limit = 500
            try:
                limit = int(self._limit_tf.value or "500")
            except ValueError:
                pass

            kw: dict = {"desc": True, "limit": limit}
            if watcher and watcher != "All":
                kw["source"] = watcher

            rows = self._manager.storage.get_raw_events(**kw)
            self._render_rows(rows)
            self._status_text.value = f"{len(rows)} rows"
        except Exception as ex:
            logger.exception("Failed to load DB data")
            self._rows_lv.controls.clear()
            self._rows_lv.controls.append(
                ft.Text(f"Error: {ex}", size=11, color=ft.Colors.RED_400),
            )
            self._status_text.value = "Failed to load"
        self._page.update()

    def _render_rows(self, rows: list[dict]):
        self._rows_lv.controls.clear()

        if not rows:
            self._rows_lv.controls.append(
                ft.Text("No data", size=13, color=ft.Colors.GREY_500),
            )
            return

        for r in rows:
            ts = datetime.datetime.fromtimestamp(r["timestamp"], tz=datetime.timezone.utc).strftime("%H:%M:%S")
            payload_str = _fmt_data(r["payload"])

            card = ft.Container(
                padding=ft.padding.Padding.only(left=8, right=8, top=6, bottom=6),
                bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.GREY_800),
                border_radius=6,
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(f"#{r['id']}", size=11, color=ft.Colors.GREY_500, width=50),
                                ft.Text(r["source"], size=11, weight=ft.FontWeight.W_600, width=130),
                                ft.Text(r["event_type"], size=11, color=ft.Colors.GREY_400, width=170),
                                ft.Text(ts, size=11, color=ft.Colors.GREY_400, width=70),
                            ],
                            spacing=4,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(
                            content=ft.Text(
                                payload_str,
                                size=11,
                                font_family="monospace",
                                selectable=True,
                                no_wrap=False,
                            ),
                            padding=ft.padding.Padding.only(top=2),
                        ),
                    ],
                    spacing=0,
                    tight=True,
                ),
            )
            self._rows_lv.controls.append(card)

    async def _export_csv(self, e=None):
        if platform.system() == "Android":
            await self._export_via_saf("csv")
        else:
            self._export_direct("csv")

    async def _export_json(self, e=None):
        if platform.system() == "Android":
            await self._export_via_saf("json")
        else:
            self._export_direct("json")

    async def _export_via_saf(self, fmt: str):
        try:
            rows = self._manager.storage.get_raw_events()
            if fmt == "csv":
                filename, data = ExportService.prepare_raw_events_csv(rows)
            else:
                filename, data = ExportService.prepare_raw_events(rows)
            result = await self._file_picker.save_file(
                file_name=filename,
                src_bytes=data,
                allowed_extensions=(["csv"] if fmt == "csv" else ["json"]),
            )
            if result is None:
                self._status_text.value = "Export cancelled"
            else:
                self._status_text.value = result
                self._page.show_dialog(
                    ft.SnackBar(content=ft.Text(f"Saved: {result}", size=12, selectable=True), open=True)
                )
        except Exception as ex:
            logger.exception("Export failed")
            self._status_text.value = "Export failed"
            self._page.show_dialog(ft.SnackBar(content=ft.Text(f"Export failed: {ex}", size=12), open=True))
        self._page.update()

    def _export_direct(self, fmt: str):
        try:
            rows = self._manager.storage.get_raw_events()
            export_dir = get_export_dir()

            if fmt == "csv":
                filename, data = ExportService.prepare_raw_events_csv(rows)
            else:
                filename, data = ExportService.prepare_raw_events(rows)
            path = os.path.join(export_dir, filename)
            with open(path, "wb") as f:
                f.write(data)

            self._status_text.value = os.path.basename(path)
            self._page.show_dialog(ft.SnackBar(content=ft.Text(path, size=12, selectable=True), open=True))
        except Exception as ex:
            logger.exception("Export failed")
            self._status_text.value = "Export failed"
            msg = f"Export failed: {ex}"
            if "Permission denied" in str(ex) or "denied" in str(ex).lower():
                msg += " — enable storage permission in system settings"
            self._page.show_dialog(ft.SnackBar(content=ft.Text(msg, size=12), open=True))
        self._page.update()


def _fmt_data(data: dict) -> str:
    parts = []
    for k, v in data.items():
        if isinstance(v, dict):
            inner = "; ".join(f"{ik}={iv}" for ik, iv in v.items())
            parts.append(f"{k}: {inner}")
        elif isinstance(v, list):
            parts.append(f"{k}: [{len(v)} items]")
        else:
            parts.append(f"{k}: {v}")
    return " | ".join(parts) if parts else "{}"

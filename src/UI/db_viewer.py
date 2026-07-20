import json
import logging
import time

import flet as ft

from core.storage import Storage

logger = logging.getLogger(__name__)

WATCHER_OPTIONS = [
    "All",
    "foreground",
    "afk",
    "power",
    "android_foreground",
    "android_afk",
    "android_power",
]


class DbViewer:
    def __init__(self, page: ft.Page, storage: Storage):
        self.page = page
        self._storage = storage

        self._watcher_dd = ft.Dropdown(
            options=[ft.dropdown.Option(w) for w in WATCHER_OPTIONS],
            value="All",
            width=140,
            dense=True,
        )
        self._limit_field = ft.TextField(value="500", width=70, dense=True, text_align=ft.TextAlign.RIGHT)
        self._refresh_btn = ft.Button("Refresh", on_click=self._load, icon=ft.Icons.REFRESH)
        self._summary_text = ft.Text("", size=11, color=ft.Colors.GREY)

        self._list_view = ft.ListView(expand=True, spacing=2, auto_scroll=False, divide=ft.Divider(height=1))

        self._view = ft.Container(
            visible=False,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BACKGROUND),
            padding=10,
            content=ft.Column(
                expand=True,
                spacing=6,
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("DB Viewer (dev)", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                controls=[
                                    self._watcher_dd,
                                    ft.Text("Max:", size=12),
                                    self._limit_field,
                                    self._refresh_btn,
                                ],
                                spacing=6,
                            ),
                            ft.IconButton(ft.Icons.CLOSE, icon_size=20, on_click=lambda e: self.hide()),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    self._summary_text,
                    ft.Container(
                        expand=True,
                        border=ft.border.all(1, ft.Colors.OUTLINE),
                        border_radius=6,
                        padding=4,
                        content=self._list_view,
                    ),
                ],
            ),
        )

    @property
    def overlay(self) -> ft.Container:
        return self._view

    def show(self) -> None:
        self._view.visible = True
        self._view.update()

    def hide(self) -> None:
        self._view.visible = False
        self._view.update()

    async def _load(self, e=None) -> None:
        watcher = self._watcher_dd.value
        try:
            max_rows = int(self._limit_field.value or "500")
        except ValueError:
            max_rows = 500

        t0 = time.time()
        rows = self._storage.get_events()
        t1 = time.time()

        if watcher != "All":
            rows = [r for r in rows if r["watcher"] == watcher]

        total = len(rows)
        rows = rows[-max_rows:]

        self._summary_text.value = f"{total} rows · {len(rows)} shown · {t1 - t0:.2f}s"

        self._list_view.controls.clear()

        if not rows:
            self._list_view.controls.append(ft.Text("No data in DB yet.", size=12, color=ft.Colors.GREY))
        else:
            for r in rows:
                ts = self._format_ts(r["timestamp"])
                dur = self._format_dur(r["duration"])
                data_str = self._format_data(r["data"])

                card = ft.Container(
                    padding=ft.padding.only(left=6, right=6, top=4, bottom=4),
                    content=ft.Column(
                        spacing=2,
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text(f"#{r['id']}", size=10, color=ft.Colors.GREY, font_family="monospace"),
                                    ft.Text(r["watcher"], size=11, weight=ft.FontWeight.BOLD),
                                    ft.Text(ts, size=11, color=ft.Colors.GREY),
                                    ft.Text(dur, size=11, color=ft.Colors.GREY),
                                ],
                                spacing=10,
                            ),
                            ft.Text(data_str, size=10, selectable=True, font_family="monospace"),
                        ],
                    ),
                )
                self._list_view.controls.append(card)

        self.page.update()

    @staticmethod
    def _format_ts(epoch_s: float) -> str:
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(epoch_s)
            return dt.strftime("%H:%M:%S")
        except (OSError, OverflowError, ValueError):
            return str(epoch_s)

    @staticmethod
    def _format_dur(dur_s: float) -> str:
        if dur_s >= 3600:
            return f"{dur_s / 3600:.1f}h"
        if dur_s >= 60:
            return f"{dur_s / 60:.1f}m"
        if dur_s >= 1:
            return f"{dur_s:.0f}s"
        if dur_s > 0:
            return f"{dur_s * 1000:.0f}ms"
        return "-"

    @staticmethod
    def _format_data(data: dict) -> str:
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(data)

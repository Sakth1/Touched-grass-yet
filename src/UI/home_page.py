import logging

import flet as ft

from UI.settings_page import SettingsPanel
from core.application.collection_manager import CollectionManager
from utils.models import SystemType, Tick

logger = logging.getLogger(__name__)

MAX_LOG_ENTRIES = 100


class HomePage:
    def __init__(self, page: ft.Page, manager: CollectionManager):
        self.page = page
        self._manager = manager
        self._settings = SettingsPanel(page)
        self._status_text = ft.Text("Status: Stopped", size=16)
        self._platform_text = ft.Text(f"Platform: {manager.system_type.name}", size=14)

        self._current_title = ft.Text("-", size=14, weight=ft.FontWeight.BOLD)

        self._start_btn = ft.Button(
            "Start Collection",
            on_click=self._handle_start,
            icon=ft.Icons.PLAY_ARROW,
        )
        self._stop_btn = ft.Button(
            "Stop Collection",
            on_click=self._handle_stop,
            icon=ft.Icons.STOP,
            disabled=True,
        )

        self._log_area = ft.ListView(
            expand=True,
            spacing=2,
            auto_scroll=True,
        )

        self.page.add(
            ft.Stack(
                controls=[
                    ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    self._status_text,
                                    ft.Row(
                                        controls=[
                                            self._platform_text,
                                            ft.IconButton(
                                                ft.Icons.SETTINGS,
                                                icon_size=20,
                                                on_click=lambda e: self._settings.show(),
                                            ),
                                        ],
                                        spacing=4,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Divider(height=5),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(
                                            "Foreground App",
                                            size=14,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        self._current_title,
                                    ],
                                    spacing=2,
                                ),
                                padding=10,
                                bgcolor=ft.Colors.SURFACE_DIM,
                                border_radius=8,
                            ),
                            ft.Divider(height=5),
                            ft.Row(
                                controls=[
                                    self._start_btn,
                                    self._stop_btn,
                                ],
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=20,
                            ),
                            ft.Divider(height=5),
                            ft.Text("Activity Log", size=14, weight=ft.FontWeight.BOLD),
                            self._log_area,
                        ],
                        expand=True,
                        spacing=3,
                    ),
                    self._settings.overlay,
                ],
                expand=True,
            )
        )

    def _on_tick(self, tick: Tick) -> None:
        if tick.watcher == "android_foreground":
            self._on_android_tick(tick)
        elif tick.watcher == "foreground":
            self._on_windows_tick(tick)

    def _on_windows_tick(self, tick: Tick) -> None:
        title = tick.data.get("title", "-")
        app = tick.data.get("app", "-")
        browser = tick.data.get("browser")
        page_title = tick.data.get("page_title")
        domain = tick.data.get("inferred_domain")

        if browser and page_title:
            display = f"{browser}: {page_title}"
            if domain:
                display += f" ({domain})"
        else:
            display = f"{app} — {title}" if title else app

        self._current_title.value = display

        ts = tick.timestamp.strftime("%H:%M:%S")
        entry = ft.Text(f"[{ts}] {display}", size=11, no_wrap=True)
        self._log_area.controls.append(entry)

        if len(self._log_area.controls) > MAX_LOG_ENTRIES:
            self._log_area.controls.pop(0)

        self.page.update()

    def _on_android_tick(self, tick: Tick) -> None:
        app_name = tick.data.get("app_name", "")
        pkg = tick.data.get("package", "")
        display = f"{app_name} ({pkg})" if app_name else pkg

        self._current_title.value = display

        ts = tick.timestamp.strftime("%H:%M:%S")
        entry = ft.Text(f"[{ts}] {display}", size=11, no_wrap=True)
        self._log_area.controls.append(entry)

        if len(self._log_area.controls) > MAX_LOG_ENTRIES:
            self._log_area.controls.pop(0)

        self.page.update()

    async def _handle_start(self, e):
        if self._manager.system_type == SystemType.ANDROID:
            from core.collectors.android.usage_stats import check_usage_stats_permission
            if not check_usage_stats_permission():
                await self.show_permission_dialog()
                return

        self._start_btn.disabled = True
        self._stop_btn.disabled = False
        self._status_text.value = "Status: Running"
        self._log_area.controls.append(ft.Text("Starting collection...", size=12))

        self._manager.bus.subscribe(self._on_tick)

        self.page.update()
        await self._manager.start()

    async def _handle_stop(self, e):
        self._manager.bus.unsubscribe(self._on_tick)

        self._start_btn.disabled = False
        self._stop_btn.disabled = True
        self._status_text.value = "Status: Stopped"
        self._log_area.controls.append(ft.Text("Stopping collection...", size=12))
        self.page.update()
        await self._manager.stop()

    async def show_permission_dialog(self):
        dlg = ft.AlertDialog(
            title=ft.Text("Usage Access Required"),
            content=ft.Text(
                "This app needs Usage Access permission to track "
                "which apps are in the foreground.\n\n"
                "Please enable it in:\n"
                "Settings → Apps → Special App Access → Usage Access",
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._close_dialog(dlg)),
                ft.ElevatedButton("Open Settings", on_click=lambda e: self._open_settings(dlg)),
            ],
        )
        self.page.open(dlg)

    def _close_dialog(self, dlg):
        self.page.close(dlg)

    def _open_settings(self, dlg):
        dlg.open = False
        self.page.update()
        from core.collectors.android.usage_stats import open_usage_access_settings
        open_usage_access_settings()

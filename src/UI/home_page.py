import flet as ft

from core.application.collection_manager import CollectionManager
from utils.models import Tick

MAX_LOG_ENTRIES = 100


class HomePage:
    def __init__(self, page: ft.Page, manager: CollectionManager):
        self.page = page
        self._manager = manager
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
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            self._status_text,
                            self._platform_text,
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
            )
        )

    def _on_tick(self, tick: Tick) -> None:
        if tick.watcher != "window":
            return

        title = tick.data.get("title", "-")
        app = tick.data.get("app", "-")
        display = f"{app} — {title}" if title else app

        self._current_title.value = display

        ts = tick.timestamp.strftime("%H:%M:%S")
        entry = ft.Text(f"[{ts}] Window: {display}", size=11, no_wrap=True)
        self._log_area.controls.append(entry)

        if len(self._log_area.controls) > MAX_LOG_ENTRIES:
            self._log_area.controls.pop(0)

        self.page.update()

    async def _handle_start(self, e):
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

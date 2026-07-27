import flet as ft

from ..services.command_registry import CommandRegistry
from ..services.state import AppState, Destination
from ..theme.tokens import RADIUS, SPACING

_COMMON_COMMANDS = [
    {"id": "nav_dashboard", "title": "Go to Dashboard", "keywords": ["home", "main"]},
    {"id": "nav_timeline", "title": "Go to Timeline", "keywords": ["history", "sessions"]},
    {"id": "nav_analytics", "title": "Go to Analytics", "keywords": ["trends", "charts"]},
    {"id": "nav_settings", "title": "Go to Settings", "keywords": ["preferences", "config"]},
]


class CommandPalette:
    def __init__(self, page: ft.Page, state: AppState, registry: CommandRegistry) -> None:
        self.page = page
        self.state = state
        self._registry = registry

        self._query = ft.TextField(
            hint_text="Search commands...",
            border=ft.InputBorder.NONE,
            text_size=16,
            autofocus=True,
            on_change=self._on_query_change,
            on_submit=self._on_submit,
            expand=True,
        )
        self._results = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)
        self._selected_index = 0
        self._current_results: list = []

        self._dialog = ft.AlertDialog(
            modal=True,
            content=ft.Container(
                width=480,
                height=400,
                padding=ft.padding.Padding.all(SPACING["sm"]),
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=self._query,
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            border_radius=RADIUS["md"],
                            padding=ft.padding.Padding.symmetric(horizontal=SPACING["sm"], vertical=2),
                        ),
                        ft.Divider(height=1),
                        self._results,
                    ],
                    spacing=SPACING["sm"],
                ),
            ),
            on_dismiss=self._on_dismiss,
        )

        self._register_common()

    def _register_common(self) -> None:
        dest_map = {
            "nav_dashboard": Destination.DASHBOARD,
            "nav_timeline": Destination.TIMELINE,
            "nav_analytics": Destination.ANALYTICS,
            "nav_settings": Destination.SETTINGS,
        }
        from ..services.command_registry import Command
        for cmd_def in _COMMON_COMMANDS:
            dest = dest_map.get(cmd_def["id"])
            self._registry.register(Command(
                id=cmd_def["id"],
                title=cmd_def["title"],
                handler=lambda d=dest: self._navigate_to(d),
                category="navigation",
                keywords=cmd_def["keywords"],
            ))

    def _navigate_to(self, destination: Destination) -> None:
        self.state.current_destination = destination
        self.close()

    def open(self) -> None:
        self._query.value = ""
        self._selected_index = 0
        self._current_results = self._registry.search("")
        self._render_results()
        self.page.show_dialog(self._dialog)
        self.page.update()

    def close(self) -> None:
        self._dialog.open = False
        self.page.update()

    def _on_dismiss(self, e: ft.ControlEvent) -> None:
        self.close()

    def _on_query_change(self, e: ft.ControlEvent) -> None:
        self._selected_index = 0
        self._current_results = self._registry.search(e.control.value or "")
        self._render_results()

    def _on_submit(self, e: ft.ControlEvent) -> None:
        if self._current_results:
            self._current_results[0].handler()
            self.close()

    def _render_results(self) -> None:
        items = []
        for i, cmd in enumerate(self._current_results):
            selected = i == self._selected_index
            items.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(cmd.title, size=14, expand=True),
                            ft.Text(cmd.shortcut or "", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ],
                        spacing=SPACING["sm"],
                    ),
                    padding=ft.padding.Padding.all(SPACING["sm"]),
                    border_radius=RADIUS["sm"],
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if selected else None,
                    ink=True,
                    on_click=lambda _, c=cmd: (c.handler(), self.close()),
                )
            )
        self._results.controls = items
        self._results.update()

    def handle_key(self, e: ft.KeyboardEvent) -> bool:
        if e.key == "K" and (e.meta or e.ctrl):
            self.open()
            return True
        return False






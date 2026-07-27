from collections.abc import Callable

import flet as ft

from ..core.breakpoints import classify_width
from ..services.command_registry import CommandRegistry
from ..services.state import AppState
from .activity_bar import ActivityBar
from .command_palette import CommandPalette
from .content_area import ContentArea
from .context_panel import ContextPanel
from .sidebar import Sidebar
from .status_bar import StatusBar


class AppShell(ft.Container):
    def __init__(
        self,
        page: ft.Page,
        state: AppState,
        registry: CommandRegistry,
        content_area: ContentArea,
    ) -> None:
        self._page = page
        self.state = state
        self._registry = registry
        self._content_area = content_area

        initial_width = page.width if page.width else 1200
        self._width_class = classify_width(initial_width)

        self._activity_bar = ActivityBar(state, self._width_class)
        self._sidebar = Sidebar(state, self._width_class)
        self._context_panel = ContextPanel(state, self._width_class)
        self._status_bar = StatusBar(state, self._width_class)
        self._command_palette = CommandPalette(page, state, registry)

        main_column = ft.Column(
            controls=[
                self._content_area,
                self._status_bar,
            ],
            spacing=0,
            expand=True,
        )

        self._main_row = ft.Row(
            controls=[
                self._activity_bar,
                self._sidebar,
                main_column,
                self._context_panel,
            ],
            spacing=0,
            expand=True,
        )

        super().__init__(
            expand=True,
            content=self._main_row,
        )

        self._dispose_fns: list[Callable[[], None]] = []

        self._dispose_fns.append(
            state.subscribe("current_destination", self._on_destination_change)
        )
        self._dispose_fns.append(
            state.subscribe("sidebar_open", self._on_sidebar_change)
        )
        self._dispose_fns.append(
            state.subscribe("context_open", self._on_context_change)
        )
        self._dispose_fns.append(
            state.subscribe("context_content", self._on_context_change)
        )
        self._dispose_fns.append(
            state.subscribe("collection_status", self._on_status_change)
        )
        self._dispose_fns.append(
            state.subscribe("today_seconds", self._on_status_change)
        )
        self._dispose_fns.append(
            state.subscribe("battery", self._on_status_change)
        )

        page.on_resize = self._on_page_resize
        page.on_keyboard_event = self._on_keyboard

    def _on_destination_change(self) -> None:
        self._activity_bar.sync_selection()
        self._sidebar.sync_destination()
        self._content_area.navigate_to(self.state.current_destination)

    def _on_sidebar_change(self) -> None:
        self._sidebar.sync_destination()

    def _on_context_change(self) -> None:
        self._context_panel.sync()

    def _on_status_change(self) -> None:
        self._status_bar.sync_status()

    def _on_page_resize(self, e: ft.ControlEvent) -> None:
        new_class = classify_width(self._page.width or 0)
        if new_class != self._width_class:
            self._width_class = new_class
            self._activity_bar.update_width_class(new_class)
            self._sidebar.update_width_class(new_class)
            self._context_panel.update_width_class(new_class)
            self._status_bar.update_width_class(new_class)
            current = self._content_area.get_current_screen()
            if current:
                current.on_resize(new_class)

    def _on_keyboard(self, e: ft.KeyboardEvent) -> None:
        if self._command_palette.handle_key(e):
            return

    def dispose(self) -> None:
        for fn in self._dispose_fns:
            fn()
        self._dispose_fns.clear()






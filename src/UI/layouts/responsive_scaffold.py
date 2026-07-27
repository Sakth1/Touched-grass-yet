import logging

import flet as ft

from UI.state.app_state import AppState

NAV_DESTINATIONS: list[dict] = [
    {"label": "Dashboard", "icon": ft.Icons.DASHBOARD, "route": "/"},
    {"label": "Timeline", "icon": ft.Icons.HISTORY, "route": "/timeline"},
    {"label": "Export", "icon": ft.Icons.FILE_UPLOAD, "route": "/export"},
    {"label": "Settings", "icon": ft.Icons.SETTINGS, "route": "/settings"},
    {"label": "About", "icon": ft.Icons.INFO, "route": "/about"},
]

ROUTE_TO_INDEX: dict[str, int] = {d["route"]: i for i, d in enumerate(NAV_DESTINATIONS)}
INDEX_TO_ROUTE: dict[int, str] = {i: d["route"] for i, d in enumerate(NAV_DESTINATIONS)}

COMPACT_BREAKPOINT = 600
MEDIUM_BREAKPOINT = 840

logger = logging.getLogger(__name__)


class ResponsiveScaffold:
    def __init__(self, page: ft.Page, state: AppState) -> None:
        self.page = page
        self.state = state
        self._current_breakpoint: str = "compact"

        self._content_switcher = ft.AnimatedSwitcher(
            content=ft.Container(expand=True),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=300,
            reverse_duration=300,
            switch_in_curve=ft.AnimationCurve.DECELERATE,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
            expand=True,
        )

        self._nav_rail = ft.NavigationRail(
            selected_index=state.current_nav_index,
            label_type=ft.NavigationRailLabelType.ALL,
            elevation=3,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationRailDestination(
                    label=d["label"],
                    icon=d["icon"],
                    selected_icon=d["icon"],
                )
                for d in NAV_DESTINATIONS
            ],
            expand=True,
        )

        self._nav_bar = ft.NavigationBar(
            selected_index=state.current_nav_index,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    label=d["label"],
                    icon=d["icon"],
                    selected_icon=d["icon"],
                )
                for d in NAV_DESTINATIONS
            ],
        )

        self._container = ft.Container(
            content=self._content_switcher,
            expand=True,
        )

        page.add(self._container)
        self._update_layout()

        page.on_resize = self._on_resize
        state.on_change("current_nav_index", self._sync_nav_from_state)

    def set_content(self, control: ft.Control) -> None:
        self._content_switcher.content = control
        self._content_switcher.update()

    def _on_resize(self, e: ft.ControlEvent | None = None) -> None:
        self._update_layout()

    def _update_layout(self) -> None:
        width = self.page.width or 0
        new_bp: str
        if width < COMPACT_BREAKPOINT:
            new_bp = "compact"
        elif width < MEDIUM_BREAKPOINT:
            new_bp = "medium"
        else:
            new_bp = "expanded"

        if new_bp == self._current_breakpoint:
            return

        self._current_breakpoint = new_bp

        if new_bp == "compact":
            self.page.navigation_bar = self._nav_bar
            self._container.content = self._content_switcher
            self._nav_rail.extended = False
        elif new_bp == "medium":
            self.page.navigation_bar = None
            self._container.content = ft.Row(
                controls=[
                    self._nav_rail,
                    ft.VerticalDivider(width=1),
                    self._content_switcher,
                ],
                expand=True,
                spacing=0,
            )
            self._nav_rail.extended = False
        else:
            self.page.navigation_bar = None
            self._container.content = ft.Row(
                controls=[
                    self._nav_rail,
                    ft.VerticalDivider(width=1),
                    self._content_switcher,
                ],
                expand=True,
                spacing=0,
            )
            self._nav_rail.extended = True

        self.page.update()

    def _on_nav_change(self, e: ft.ControlEvent) -> None:
        index = e.control.selected_index
        self.state.current_nav_index = index
        route = INDEX_TO_ROUTE[index]
        self.page.go(route)

    def _sync_nav_from_state(self) -> None:
        index = self.state.current_nav_index
        if self._nav_bar.selected_index != index:
            self._nav_bar.selected_index = index
        if self._nav_rail.selected_index != index:
            self._nav_rail.selected_index = index
        try:
            self._nav_bar.update()
            self._nav_rail.update()
        except Exception:
            pass

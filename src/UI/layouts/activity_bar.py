import flet as ft

from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState, Destination
from ..theme.tokens import SPACING

_DEST_ICONS: dict[Destination, tuple[str, str]] = {
    Destination.DASHBOARD: (ft.Icons.DASHBOARD, "Dashboard"),
    Destination.TIMELINE: (ft.Icons.HISTORY, "Timeline"),
    Destination.ANALYTICS: (ft.Icons.ANALYTICS, "Analytics"),
    Destination.SETTINGS: (ft.Icons.SETTINGS, "Settings"),
}


class ActivityBar(ft.Container):
    def __init__(self, state: AppState, width_class: WindowWidthClass) -> None:
        self.state = state
        self.width_class = width_class
        self._buttons: dict[Destination, ft.IconButton] = {}

        icons = []
        for dest, (icon, label) in _DEST_ICONS.items():
            btn = ft.IconButton(
                icon=icon,
                tooltip=label,
                selected=dest == state.current_destination,
                icon_size=22,
                on_click=lambda _, d=dest: self._navigate(d),
            )
            self._buttons[dest] = btn
            icons.append(btn)

        super().__init__(
            width=48,
            expand=False,
            padding=ft.padding.Padding.symmetric(vertical=SPACING["sm"]),
            bgcolor=ft.Colors.SURFACE_CONTAINER if self._is_desktop() else None,
            content=ft.Column(
                controls=icons,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=SPACING["xs"],
            ),
        )

    def _is_desktop(self) -> bool:
        return self.width_class in (WindowWidthClass.EXPANDED, WindowWidthClass.MEDIUM)

    def _navigate(self, destination: Destination) -> None:
        self.state.current_destination = destination
        if self.width_class == WindowWidthClass.COMPACT:
            self.state.sidebar_open = False
        elif self.width_class == WindowWidthClass.EXPANDED:
            self.state.sidebar_open = True

    def sync_selection(self) -> None:
        current = self.state.current_destination
        for dest, btn in self._buttons.items():
            btn.selected = dest == current
            btn.update()

    def update_width_class(self, width_class: WindowWidthClass) -> None:
        self.width_class = width_class
        self.bgcolor = ft.Colors.SURFACE_CONTAINER if self._is_desktop() else None
        self.update()






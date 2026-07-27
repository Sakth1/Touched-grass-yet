import flet as ft

from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState, CollectionStatus
from ..theme.tokens import SPACING

_COL_STATUS_COLORS = {
    CollectionStatus.RUNNING: ft.Colors.GREEN,
    CollectionStatus.PAUSED: ft.Colors.ORANGE,
    CollectionStatus.STOPPED: ft.Colors.GREY,
}


class StatusBar(ft.Container):
    def __init__(self, state: AppState, width_class: WindowWidthClass) -> None:
        self.state = state
        self.width_class = width_class

        self._status_dot = ft.Container(
            width=8,
            height=8,
            border_radius=4,
            bgcolor=_COL_STATUS_COLORS.get(state.collection_status, ft.Colors.GREY),
        )
        self._status_label = ft.Text(
            state.collection_status.name.capitalize(),
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self._today_label = ft.Text(
            self._format_today(state.today_seconds),
            size=11,
            color=ft.Colors.ON_SURFACE_VARIANT,
            weight=ft.FontWeight.W_500,
        )
        self._battery_icon = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT)
        self._version_label = ft.Text("v0.4.1", size=11, color=ft.Colors.ON_SURFACE_VARIANT)

        left = ft.Row(
            controls=[
                self._status_dot,
                self._status_label,
            ],
            spacing=SPACING["xs"],
        )
        right = ft.Row(
            controls=[
                self._battery_icon,
                ft.Container(width=1, height=12, bgcolor=ft.Colors.OUTLINE_VARIANT),
                self._today_label,
                ft.Container(width=1, height=12, bgcolor=ft.Colors.OUTLINE_VARIANT),
                self._version_label,
            ],
            spacing=SPACING["sm"],
        )

        super().__init__(
            height=32,
            padding=ft.padding.Padding.symmetric(horizontal=SPACING["md"]),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            content=ft.Row(
                controls=[left, right],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )

    def _format_today(self, seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"Today: {hours}h {minutes:02d}m"

    def sync_status(self) -> None:
        status = self.state.collection_status
        self._status_dot.bgcolor = _COL_STATUS_COLORS.get(status, ft.Colors.GREY)
        self._status_label.value = status.name.capitalize()
        self._today_label.value = self._format_today(self.state.today_seconds)
        self._update_battery()
        self.update()

    def _update_battery(self) -> None:
        pct = self.state.battery_pct
        charging = self.state.battery_charging
        if pct is not None:
            icon = "🔋" if not charging else "⚡"
            self._battery_icon.value = f"{icon} {pct}%"
        else:
            self._battery_icon.value = ""

    def update_width_class(self, width_class: WindowWidthClass) -> None:
        self.width_class = width_class
        self.update()






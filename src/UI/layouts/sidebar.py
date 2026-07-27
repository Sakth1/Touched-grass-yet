import flet as ft

from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState, Destination
from ..theme.tokens import RADIUS, SPACING

_DEST_NAV: dict[Destination, list[dict]] = {
    Destination.DASHBOARD: [
        {"icon": ft.Icons.TODAY, "label": "Today"},
        {"icon": ft.Icons.STAR, "label": "Favorites"},
    ],
    Destination.TIMELINE: [
        {"icon": ft.Icons.CALENDAR_TODAY, "label": "Today"},
        {"icon": ft.Icons.CALENDAR_MONTH, "label": "This Week"},
        {"icon": ft.Icons.CALENDAR_MONTH, "label": "This Month"},
    ],
    Destination.ANALYTICS: [
        {"icon": ft.Icons.BAR_CHART, "label": "Overview"},
        {"icon": ft.Icons.APPS, "label": "By App"},
        {"icon": ft.Icons.TRENDING_UP, "label": "Trends"},
    ],
    Destination.SETTINGS: [
        {"icon": ft.Icons.TUNE, "label": "General"},
        {"icon": ft.Icons.PALETTE, "label": "Appearance"},
        {"icon": ft.Icons.SHIELD, "label": "Privacy"},
        {"icon": ft.Icons.INFO, "label": "About"},
    ],
}


class Sidebar(ft.Container):
    def __init__(self, state: AppState, width_class: WindowWidthClass) -> None:
        self.state = state
        self.width_class = width_class
        self._nav_items: list[ft.Control] = []
        self._header = ft.Text("", size=11, weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT)

        content = ft.Column(
            controls=[
                ft.Container(
                    content=self._header,
                    padding=ft.padding.Padding.only(
                        left=SPACING["md"],
                        top=SPACING["md"],
                        bottom=SPACING["xs"],
                    ),
                ),
                ft.Column(
                    ref=ft.Ref[ft.Column](),
                    spacing=2,
                ),
            ],
            spacing=0,
        )

        open_width = 200
        super().__init__(
            width=open_width if self._should_show() else 0,
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            bgcolor=ft.Colors.SURFACE_CONTAINER if self._should_show() else None,
            padding=ft.padding.Padding.only(right=1),
            content=content if self._should_show() else None,
        )
        self._open_width = open_width

    def _should_show(self) -> bool:
        return self.width_class == WindowWidthClass.EXPANDED and self.state.sidebar_open

    def _build_nav(self) -> None:
        dest = self.state.current_destination
        items = _DEST_NAV.get(dest, [])
        self._nav_items = []
        for item in items:
            btn = ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(item["icon"], size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(item["label"], size=13, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    spacing=SPACING["sm"],
                ),
                padding=ft.padding.Padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["xs"] + 2),
                border_radius=RADIUS["md"],
                ink=False,
                on_click=lambda _, lbl=item["label"]: self._on_secondary_nav(lbl),
            )
            self._nav_items.append(btn)

        header_texts = {
            Destination.DASHBOARD: "Overview",
            Destination.TIMELINE: "Date Range",
            Destination.ANALYTICS: "Analytics",
            Destination.SETTINGS: "Settings",
        }
        self._header.value = header_texts.get(dest, "")
        self.content = self._rebuild()

    def _on_secondary_nav(self, label: str) -> None:
        pass

    def _rebuild(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Container(
                    content=self._header,
                    padding=ft.padding.Padding.only(left=SPACING["md"], top=SPACING["md"], bottom=SPACING["xs"]),
                ),
                ft.Column(controls=self._nav_items, spacing=2),
            ],
            spacing=0,
        )

    def sync_destination(self) -> None:
        self._build_nav()
        show = self._should_show()
        self.width = self._open_width if show else 0
        self.bgcolor = ft.Colors.SURFACE_CONTAINER if show else None
        if not show:
            self.content = None
        else:
            self._build_nav()
        self.update()

    def update_width_class(self, width_class: WindowWidthClass) -> None:
        self.width_class = width_class
        self.sync_destination()

    def toggle(self) -> None:
        self.state.sidebar_open = not self.state.sidebar_open
        self.sync_destination()






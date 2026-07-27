import flet as ft

from ..components import ActivityStrip, AppCard
from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState
from ..theme.tokens import RADIUS, SEED_COLORS, SPACING
from .base_screen import BaseScreen

_COLORS = list(SEED_COLORS.values())


class DashboardScreen(BaseScreen):
    def __init__(self, state: AppState) -> None:
        self._greeting = ft.Text(size=24, weight=ft.FontWeight.W_600)
        self._total_time = ft.Text(size=48, weight=ft.FontWeight.W_700)
        self._total_label = ft.Text("", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        self._apps_row = ft.Row(spacing=SPACING["sm"], scroll=ft.ScrollMode.AUTO)
        self._activity = ActivityStrip()
        self._timeline_col = ft.Column(spacing=2)

        super().__init__(state)

        self.bind_state("today_seconds", self._on_data_change)
        self.bind_state("top_apps", self._on_data_change)

    def _on_data_change(self) -> None:
        self._refresh()
        self.update()

    def build_content(self) -> ft.Control:
        self._refresh()
        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            self._greeting,
                            ft.Container(height=SPACING["xs"]),
                            self._total_time,
                            self._total_label,
                        ],
                        spacing=0,
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Top Apps Today", size=13,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                            self._apps_row,
                        ],
                        spacing=SPACING["sm"],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Activity", size=13,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                            self._activity,
                        ],
                        spacing=SPACING["xs"],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Recent Activity", size=13,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                            self._timeline_col,
                        ],
                        spacing=SPACING["xs"],
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                    expand=True,
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )
        self.content = content
        return self

    def _refresh(self) -> None:
        hour = __import__("datetime").datetime.now().hour
        if hour < 12:
            self._greeting.value = "Good morning"
        elif hour < 17:
            self._greeting.value = "Good afternoon"
        else:
            self._greeting.value = "Good evening"

        today_seconds = self.state.today_seconds
        h = int(today_seconds // 3600)
        m = int((today_seconds % 3600) // 60)
        self._total_time.value = f"{h}h {m:02d}m"
        self._total_label.value = "screen time today"

        top_apps = self.state.top_apps
        if top_apps:
            self._apps_row.controls = [
                AppCard(
                    app_name=a.app_key,
                    duration_text=self._fmt_duration(a.total_seconds),
                    fraction=a.total_seconds / max(today_seconds, 1),
                    color=_COLORS[i % len(_COLORS)],
                    on_click=lambda _, n=a.app_key: self._show_app_detail(n),
                )
                for i, a in enumerate(top_apps)
            ]
        else:
            mock_apps = [
                ("VS Code", 7920),
                ("Chrome", 6300),
                ("Terminal", 2700),
                ("Slack", 1920),
                ("Spotify", 1080),
            ]
            self._apps_row.controls = [
                AppCard(
                    app_name=name,
                    duration_text=self._fmt_duration(dur),
                    color=_COLORS[i % len(_COLORS)],
                    on_click=lambda _, n=name: self._show_app_detail(n),
                )
                for i, (name, dur) in enumerate(mock_apps)
            ]

        self._timeline_col.controls = [
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(
                            width=max(4, min(m * 8, 200)),
                            height=20,
                            border_radius=RADIUS["sm"],
                            bgcolor=color,
                        ),
                        ft.Text(f"{m}m", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Text(name, size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                    ],
                    spacing=SPACING["xs"],
                ),
                margin=ft.margin.Margin.symmetric(vertical=1),
            )
            for m, name, color in [
                (15, "VS Code", ft.Colors.BLUE),
                (10, "Chrome", ft.Colors.GREEN),
                (20, "VS Code", ft.Colors.BLUE),
                (8, "Terminal", ft.Colors.PURPLE),
                (12, "Slack", ft.Colors.ORANGE),
            ]
        ]

    @staticmethod
    def _fmt_duration(seconds: float) -> str:
        if seconds < 60:
            return f"{int(seconds)}s"
        m = int(seconds // 60)
        return f"{m}m"

    def _show_app_detail(self, app_name: str) -> None:
        controls = [
            ft.Text(f"Today's usage for {app_name}", size=14),
            ft.Text("Total: 2h 12m", size=13),
            ft.Text("Sessions: 4", size=13),
            ft.Text("Longest session: 45m", size=13),
        ]
        parent = self._find_parent()
        if parent:
            parent.set_content(app_name, controls)

    def _find_parent(self):
        p = self.parent
        while p:
            if hasattr(p, "set_content"):
                return p
            p = getattr(p, "parent", None)
        return None

    def on_resize(self, width_class: WindowWidthClass) -> None:
        if width_class == WindowWidthClass.COMPACT:
            pass






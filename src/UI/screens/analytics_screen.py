import flet as ft

from ..services.state import AppState
from ..theme.tokens import RADIUS, SPACING
from .base_screen import BaseScreen

_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class AnalyticsScreen(BaseScreen):
    def __init__(self, state: AppState) -> None:
        self._period_selector = ft.Dropdown(
            value="This Week",
            options=[
                ft.dropdown.Option("Today"),
                ft.dropdown.Option("This Week"),
                ft.dropdown.Option("This Month"),
            ],
            width=160,
        )
        self._period_selector.on_change = self._on_period_change

        self._daily_chart = ft.Column(spacing=4)
        self._weekly_stat = ft.Text("", size=14, color=ft.Colors.ON_SURFACE_VARIANT)
        self._change_stat = ft.Text("", size=14)
        self._focus_score = ft.Text("72", size=48, weight=ft.FontWeight.W_700)
        self._focus_detail = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        super().__init__(state)

    def build_content(self) -> ft.Control:
        self._load_data()
        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Text("Analytics", size=24, weight=ft.FontWeight.W_600),
                                    self._period_selector,
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                        ],
                        spacing=SPACING["sm"],
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Daily Screen Time", size=13,
                                    weight=ft.FontWeight.W_600, color=ft.Colors.ON_SURFACE_VARIANT),
                            self._daily_chart,
                        ],
                        spacing=SPACING["sm"],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Weekly Total", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                        self._weekly_stat,
                                        self._change_stat,
                                    ],
                                    spacing=SPACING["xs"],
                                ),
                                padding=ft.padding.Padding.all(SPACING["md"]),
                                border_radius=RADIUS["lg"],
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text("Focus Score", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                                        self._focus_score,
                                        self._focus_detail,
                                    ],
                                    spacing=SPACING["xs"],
                                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                padding=ft.padding.Padding.all(SPACING["md"]),
                                border_radius=RADIUS["lg"],
                                bgcolor=ft.Colors.SURFACE_CONTAINER,
                                expand=True,
                                alignment=ft.Alignment.CENTER,
                            ),
                        ],
                        spacing=SPACING["md"],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )
        self.content = content
        return self

    def _load_data(self) -> None:
        mock_values = [192, 241, 165, 312, 280, 198, 145]
        max_val = max(mock_values) if mock_values else 1
        self._daily_chart.controls = [
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Text(day, size=11, width=30, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(
                            expand=True,
                            height=28,
                            border_radius=RADIUS["sm"],
                            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                            content=ft.Container(
                                width=max(28, int((val / max_val) * 300)),
                                height=28,
                                border_radius=RADIUS["sm"],
                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                alignment=ft.Alignment.CENTER_RIGHT,
                                padding=ft.padding.Padding.only(right=SPACING["sm"]),
                                content=ft.Text(f"{val // 60}h {val % 60}m",
                                                size=10, color=ft.Colors.ON_PRIMARY_CONTAINER),
                            ),
                        ),
                    ],
                    spacing=SPACING["sm"],
                ),
                margin=ft.margin.Margin.symmetric(vertical=2),
            )
            for day, val in zip(_DAYS, mock_values, strict=True)
        ]

        total = sum(mock_values)
        self._weekly_stat.value = f"{total // 60}h {total % 60}m"
        self._change_stat.value = "▲ +10% vs last week"
        self._change_stat.color = ft.Colors.GREEN
        self._focus_detail.value = "▲ up 5% from last week"

    def _on_period_change(self, e: ft.ControlEvent) -> None:
        self._load_data()
        self.update()






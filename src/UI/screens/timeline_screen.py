from datetime import date

import flet as ft

from ..components import DateNavigator, SessionCard
from ..services.state import AppState
from ..theme.tokens import RADIUS, SPACING
from .base_screen import BaseScreen


class TimelineScreen(BaseScreen):
    def __init__(self, state: AppState) -> None:
        self._selected_date = date.today()
        self._nav = DateNavigator(on_change=self._on_date_change)
        self._total_label = ft.Text("", size=14, color=ft.Colors.ON_SURFACE_VARIANT)
        self._most_label = ft.Text("", size=14, color=ft.Colors.ON_SURFACE_VARIANT)

        self._bar_chart = ft.Column(spacing=4)
        self._session_list = ft.Column(spacing=2, scroll=ft.ScrollMode.AUTO)

        super().__init__(state)

    def build_content(self) -> ft.Control:
        self._load_data()
        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Timeline", size=24, weight=ft.FontWeight.W_600),
                            self._nav,
                            ft.Row(
                                controls=[self._total_label, self._most_label],
                                spacing=SPACING["lg"],
                            ),
                        ],
                        spacing=SPACING["sm"],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Apps Used", size=13, weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE_VARIANT),
                            self._bar_chart,
                        ],
                        spacing=SPACING["sm"],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Text("Sessions", size=13, weight=ft.FontWeight.W_600,
                                    color=ft.Colors.ON_SURFACE_VARIANT),
                            self._session_list,
                        ],
                        spacing=SPACING["sm"],
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

    def _load_data(self) -> None:
        mock_sessions = [
            ("VS Code", "09:15", "11:27", "2h 12m", ft.Colors.BLUE, "Wireframe design"),
            ("Chrome", "10:30", "11:15", "45m", ft.Colors.GREEN, "Research"),
            ("Terminal", "11:15", "12:00", "45m", ft.Colors.PURPLE),
            ("Slack", "12:00", "12:32", "32m", ft.Colors.ORANGE, "Team chat"),
            ("Spotify", "13:00", "13:18", "18m", ft.Colors.TEAL),
        ]

        self._total_label.value = "Total: 4h 32m"
        self._most_label.value = "Most used: VS Code (2h 12m)"

        max_seconds = 7920
        self._bar_chart.controls = []
        for name, _, _, dur, color, *_rest in mock_sessions:
            seconds = sum(int(x) * 60 for x in dur.replace("h", " ").replace("m", "").split())
            frac = min(seconds / max_seconds, 1.0) if max_seconds > 0 else 0
            self._bar_chart.controls.append(
                ft.Container(
                    content=ft.Row(
                        controls=[
                            ft.Text(name, size=12, width=70, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Container(
                                expand=True,
                                height=22,
                                border_radius=RADIUS["sm"],
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                content=ft.Container(
                                    width=max(22, int(frac * 300)),
                                    height=22,
                                    border_radius=RADIUS["sm"],
                                    bgcolor=color,
                                ),
                            ),
                            ft.Text(dur, size=12, width=60, text_align=ft.TextAlign.RIGHT),
                        ],
                        spacing=SPACING["sm"],
                    ),
                    margin=ft.margin.Margin.symmetric(vertical=1),
                )
            )

        self._session_list.controls = [
            SessionCard(
                app_name=name,
                start_time=start,
                end_time=end,
                duration_text=dur,
                color=color,
                subtitle=sub if len(row) > 5 else None,
                on_click=lambda _, n=name: self._show_session_detail(n),
            )
            for name, start, end, dur, color, *rest in mock_sessions
            for sub in ([rest[0]] if rest else [None])
            for row in [[name, start, end, dur, color] + ([rest[0]] if rest else [])]
        ]

    def _on_date_change(self, d: date) -> None:
        self._selected_date = d
        self._load_data()
        self.update()

    def _show_session_detail(self, app_name: str) -> None:
        controls = [
            ft.Text(f"Session: {app_name}", size=14),
            ft.Text("Duration: 2h 12m", size=13),
            ft.Text("Browser: Chrome", size=13),
            ft.Text("Pages visited: 12", size=13),
            ft.Text("Category: Development", size=13),
        ]
        self.state.context_content = {"title": app_name, "controls": controls}
        self.state.context_open = True






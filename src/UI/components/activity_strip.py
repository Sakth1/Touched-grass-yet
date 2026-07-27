from typing import Any

import flet as ft

from ..theme.tokens import RADIUS, SPACING


class ActivityStrip(ft.Container):
    def __init__(
        self,
        active_seconds: float = 0.0,
        idle_seconds: float = 0.0,
        away_seconds: float = 0.0,
        **kwargs: Any,
    ) -> None:
        def _fmt(s: float) -> str:
            m = int(s // 60)
            return f"{m}m" if m > 0 else f"{int(s)}s"

        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Stack(
                        controls=[
                            ft.Container(height=8, bgcolor=ft.Colors.ERROR_CONTAINER, border_radius=RADIUS["full"]),
                        ],
                    ),
                    ft.Row(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.PRIMARY),
                                    ft.Text(f"Active {_fmt(active_seconds)}", size=11,
        color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=SPACING["xs"],
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.TERTIARY),
                                    ft.Text(f"Idle {_fmt(idle_seconds)}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=SPACING["xs"],
                            ),
                            ft.Row(
                                controls=[
                                    ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.ERROR),
                                    ft.Text(f"Away {_fmt(away_seconds)}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ],
                                spacing=SPACING["xs"],
                            ),
                        ],
                        spacing=SPACING["md"],
                    ),
                ],
                spacing=SPACING["xs"],
            ),
            **kwargs,
        )






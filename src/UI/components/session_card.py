from typing import Any

import flet as ft

from ..theme.tokens import RADIUS, SPACING


class SessionCard(ft.Container):
    def __init__(
        self,
        app_name: str,
        start_time: str,
        end_time: str,
        duration_text: str,
        color: str = ft.Colors.PRIMARY,
        subtitle: str | None = None,
        on_click: Any = None,
        **kwargs: Any,
    ) -> None:
        initial = app_name[0].upper() if app_name else "?"

        content = ft.Row(
            controls=[
                ft.Container(
                    width=36,
                    height=36,
                    border_radius=RADIUS["md"],
                    bgcolor=color,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(initial, size=16, weight=ft.FontWeight.W_600, color=ft.Colors.ON_PRIMARY),
                ),
                ft.Column(
                    controls=[
                        ft.Text(app_name, size=14, weight=ft.FontWeight.W_500),
                        ft.Row(
                            controls=[
                                ft.Text(f"{start_time} - {end_time}", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                (ft.Text(subtitle, size=11, color=ft.Colors.ON_SURFACE_VARIANT)
                             if subtitle else ft.Container()),
                            ],
                            spacing=SPACING["sm"],
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Text(duration_text, size=13, weight=ft.FontWeight.W_600),
                    alignment=ft.Alignment.CENTER_RIGHT,
                ),
            ],
            spacing=SPACING["sm"],
        )

        super().__init__(
            content=content,
            padding=ft.padding.Padding.all(SPACING["sm"]),
            border_radius=RADIUS["md"],
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            ink=True,
            on_click=on_click,
            **kwargs,
        )






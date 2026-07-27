from typing import Any

import flet as ft

from ..theme.tokens import RADIUS, SPACING


class AppCard(ft.Container):
    def __init__(
        self,
        app_name: str,
        duration_text: str,
        fraction: float = 0.0,
        color: str = ft.Colors.PRIMARY,
        on_click: Any = None,
        **kwargs: Any,
    ) -> None:
        initial = app_name[0].upper() if app_name else "?"

        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Container(
                        width=40,
                        height=40,
                        border_radius=RADIUS["md"],
                        bgcolor=color,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Text(
                            initial,
                            size=18,
                            weight=ft.FontWeight.W_600,
                            color=ft.Colors.ON_PRIMARY,
                        ),
                    ),
                    ft.Text(app_name, size=12, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER),
                    ft.Text(duration_text, size=11, color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                ],
                spacing=SPACING["xs"],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.Padding.all(SPACING["sm"]),
            border_radius=RADIUS["lg"],
            ink=True,
            on_click=on_click,
            **kwargs,
        )






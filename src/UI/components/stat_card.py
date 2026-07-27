from typing import Any

import flet as ft

from ..theme.tokens import SPACING


class StatCard(ft.Card):
    def __init__(
        self,
        icon: ft.Icons,
        label: str,
        value: str,
        trend: str | None = None,
        trend_up: bool = True,
        **kwargs: Any,
    ) -> None:
        trend_color = ft.Colors.GREEN if trend_up else ft.Colors.RED
        trend_icon = ft.Icons.TRENDING_UP if trend_up else ft.Icons.TRENDING_DOWN

        controls = [
            ft.Row(
                controls=[
                    ft.Icon(icon, size=20, color=ft.Colors.PRIMARY),
                    ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                spacing=SPACING["xs"],
            ),
            ft.Text(value, size=28, weight=ft.FontWeight.W_700),
        ]

        if trend is not None:
            controls.append(
                ft.Row(
                    controls=[
                        ft.Icon(trend_icon, size=14, color=trend_color),
                        ft.Text(trend, size=12, color=trend_color),
                    ],
                    spacing=2,
                )
            )

        super().__init__(
            content=ft.Container(
                content=ft.Column(controls=controls, spacing=SPACING["xs"]),
                padding=ft.padding.Padding.all(SPACING["md"]),
            ),
            elevation=1,
            **kwargs,
        )






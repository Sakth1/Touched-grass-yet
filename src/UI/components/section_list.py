from typing import Any

import flet as ft

from ..theme.tokens import RADIUS, SPACING


class SectionList(ft.Column):
    def __init__(
        self,
        sections: list[dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        items = []
        for section in sections:
            title = section.get("title", "")
            controls = section.get("controls", [])

            items.append(
                ft.Text(title, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY)
            )
            for ctrl in controls:
                items.append(ctrl)
            items.append(ft.Container(height=SPACING["sm"]))

        super().__init__(
            controls=items,
            spacing=SPACING["xs"],
            **kwargs,
        )


class SettingsSection(ft.Container):
    def __init__(
        self,
        title: str,
        description: str | None = None,
        controls: list[ft.Control] | None = None,
        **kwargs: Any,
    ) -> None:
        items: list[ft.Control] = [
            ft.Text(title, size=16, weight=ft.FontWeight.W_600),
        ]
        if description:
            items.append(
                ft.Text(description, size=12, color=ft.Colors.ON_SURFACE_VARIANT)
            )
        if controls:
            items.append(ft.Column(controls=controls, spacing=SPACING["sm"]))

        super().__init__(
            content=ft.Column(controls=items, spacing=SPACING["sm"]),
            padding=ft.padding.Padding.all(SPACING["md"]),
            border_radius=RADIUS["lg"],
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            **kwargs,
        )


class SettingsTile(ft.Container):
    def __init__(
        self,
        label: str,
        subtitle: str | None = None,
        trailing: ft.Control | None = None,
        on_click: Any = None,
        **kwargs: Any,
    ) -> None:
        items: list[ft.Control] = [
            ft.Text(label, size=14, expand=True),
        ]
        if subtitle:
            items.append(
                ft.Text(subtitle, size=11, color=ft.Colors.ON_SURFACE_VARIANT)
            )

        row = ft.Row(
            controls=[
                ft.Column(controls=[items[0]] + ([items[1]] if subtitle else []), spacing=2, expand=True),
            ],
            spacing=SPACING["sm"],
        )
        if trailing:
            row.controls.append(trailing)

        super().__init__(
            content=row,
            padding=ft.padding.Padding.symmetric(horizontal=SPACING["md"], vertical=SPACING["sm"]),
            ink=True,
            on_click=on_click,
            **kwargs,
        )






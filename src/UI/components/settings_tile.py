import flet as ft


class SettingsTile(ft.Container):
    def __init__(
        self,
        icon: ft.Control,
        label: str,
        trailing: ft.Control | None = None,
        on_click: ft.ControlEventHandler | None = None,
    ) -> None:
        super().__init__()
        tile = ft.ListTile(
            leading=icon,
            title=ft.Text(label, style=ft.TextThemeStyle.BODY_LARGE),
            trailing=trailing,
            on_click=on_click,
        )
        self.content = tile






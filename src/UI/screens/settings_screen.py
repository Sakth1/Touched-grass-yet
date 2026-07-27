import flet as ft


class SettingsScreen(ft.Container):
    def __init__(self) -> None:
        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.SETTINGS, size=48),
                    ft.Text("Settings", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Text(
                        "Settings will appear here.",
                        style=ft.TextThemeStyle.BODY_MEDIUM,
                    ),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=16,
                expand=True,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
        )

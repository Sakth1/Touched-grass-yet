import flet as ft


class AboutScreen(ft.Container):
    def __init__(self) -> None:
        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.INFO, size=48),
                    ft.Text("About", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Text(
                        "App information and updates will appear here.",
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

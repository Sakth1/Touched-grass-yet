import flet as ft


class DashboardScreen(ft.Container):
    def __init__(self) -> None:
        super().__init__(
            content=ft.Column(
                controls=[
                    ft.Icon(ft.Icons.DASHBOARD, size=48),
                    ft.Text("Dashboard", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
                    ft.Text(
                        "Collection controls will appear here.",
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

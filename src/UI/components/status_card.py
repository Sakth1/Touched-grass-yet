import flet as ft


class StatusCard(ft.Card):
    def __init__(
        self,
        icon: ft.Control,
        title: str,
        value: str,
        footer: ft.Control | None = None,
    ) -> None:
        super().__init__()
        self.content = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[icon, ft.Text(title, style=ft.TextThemeStyle.TITLE_MEDIUM)],
                        spacing=8,
                    ),
                    ft.Text(value, style=ft.TextThemeStyle.HEADLINE_SMALL),
                    *([footer] if footer else []),
                ],
                spacing=8,
            ),
            padding=ft.padding.Padding.all(16),
        )






import flet as ft


class EmptyState(ft.Container):
    def __init__(
        self,
        icon: ft.Control,
        headline: str,
        body: str,
        action_text: str | None = None,
        on_action: ft.ControlEventHandler | None = None,
    ) -> None:
        controls: list[ft.Control] = [
            icon,
            ft.Text(headline, style=ft.TextThemeStyle.HEADLINE_SMALL),
            ft.Text(body, style=ft.TextThemeStyle.BODY_MEDIUM, text_align=ft.TextAlign.CENTER),
        ]
        if action_text and on_action:
            controls.append(ft.FilledTonalButton(content=ft.Text(action_text), on_click=on_action))

        super().__init__(
            content=ft.Column(
                controls=controls,
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=12,
            ),
            alignment=ft.Alignment.CENTER,
            expand=True,
        )






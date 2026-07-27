import logging
import traceback

import flet as ft

logger = logging.getLogger(__name__)


class ErrorBoundary(ft.Container):
    def __init__(
        self,
        content_builder: ft.ControlEventHandler,
        fallback: ft.Control | None = None,
    ) -> None:
        self._builder = content_builder
        self._fallback = fallback
        built: ft.Control
        try:
            built = content_builder()
        except Exception:
            logger.exception("ErrorBoundary caught error")
            built = fallback or self._default_fallback()
        super().__init__(content=built, expand=True)

    def _default_fallback(self) -> ft.Column:
        return ft.Column(
            controls=[
                ft.Icon(ft.Icons.ERROR_OUTLINE, size=48),
                ft.Text("Something went wrong", style=ft.TextThemeStyle.TITLE_MEDIUM),
                ft.Text(
                    traceback.format_exc(),
                    style=ft.TextThemeStyle.BODY_SMALL,
                    no_wrap=False,
                ),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            expand=True,
        )

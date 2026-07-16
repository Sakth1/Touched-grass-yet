import flet as ft

from core.logging_setup import read_log_lines

MAX_VISIBLE_LINES = 500


class SettingsPanel:
    def __init__(self, page: ft.Page):
        self._page = page
        self._controls_built = False
        self._log_text = ft.Text("", size=11, font_family="monospace", selectable=True)
        self._log_scroll = ft.ListView(
            controls=[self._log_text],
            expand=True,
            auto_scroll=False,
            spacing=0,
        )
        self._status_text = ft.Text("", size=12, color=ft.Colors.GREY_400)

        self._build()

    def _build(self):
        self._view = ft.Container(
            visible=False,
            expand=True,
            bgcolor=ft.Colors.with_opacity(0.95, ft.Colors.BLACK),
            padding=20,
            content=ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Settings", size=22, weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                ft.Icons.CLOSE,
                                on_click=lambda e: self.hide(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Divider(height=10),
                    ft.ElevatedButton(
                        "View App Log",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=self._load_log,
                    ),
                    ft.Row(
                        controls=[
                            ft.ElevatedButton(
                                "Refresh",
                                icon=ft.Icons.REFRESH,
                                on_click=self._load_log,
                                visible=False,
                            ),
                            ft.ElevatedButton(
                                "Copy to Clipboard",
                                icon=ft.Icons.COPY,
                                on_click=self._copy_log,
                                visible=False,
                            ),
                        ],
                        spacing=10,
                    ),
                    self._status_text,
                    ft.Container(
                        content=self._log_scroll,
                        border=ft.border.all(1, ft.Colors.GREY_700),
                        border_radius=6,
                        padding=8,
                        expand=True,
                        bgcolor=ft.Colors.with_opacity(0.3, ft.Colors.GREY_900),
                    ),
                ],
                expand=True,
                spacing=8,
            ),
        )

    def show(self):
        self._view.visible = True
        self._page.update()

    def hide(self):
        self._view.visible = False
        self._page.update()

    @property
    def overlay(self) -> ft.Container:
        return self._view

    def _load_log(self, e=None):
        lines = read_log_lines(MAX_VISIBLE_LINES)
        if not lines:
            self._log_text.value = "No log file found."
            self._status_text.value = ""
        else:
            self._log_text.value = "".join(lines)
            self._status_text.value = f"Showing last {len(lines)} lines"
        self._page.update()

    def _copy_log(self, e=None):
        text = self._log_text.value or ""
        if text:
            self._page.set_clipboard(text)
            self._status_text.value = "Copied to clipboard"
            self._page.update()

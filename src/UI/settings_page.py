import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.logging_setup import read_log_lines

logger = logging.getLogger(__name__)

MAX_VISIBLE_LINES = 500


class SettingsPanel:
    def __init__(self, page: ft.Page, manager: CollectionManager):
        self._page = page
        self._manager = manager
        self._status_text = ft.Text("", size=12, color=ft.Colors.GREY_400)
        self._log_scroll = ft.ListView(
            expand=True,
            auto_scroll=False,
            spacing=0,
        )

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
                    ft.Button(
                        "View App Log",
                        icon=ft.Icons.DESCRIPTION,
                        on_click=self._load_log,
                    ),
                    ft.Divider(height=5),
                    ft.Button(
                        "Clear All Data",
                        icon=ft.Icons.DELETE_FOREVER,
                        on_click=self._confirm_clear_data,
                        color=ft.Colors.RED_400,
                    ),
                    ft.Row(
                        controls=[
                            ft.Button(
                                "Refresh",
                                icon=ft.Icons.REFRESH,
                                on_click=self._load_log,
                                visible=False,
                            ),
                            ft.Button(
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
                        border=ft.Border(
                            left=ft.BorderSide(1, ft.Colors.GREY_700),
                            top=ft.BorderSide(1, ft.Colors.GREY_700),
                            right=ft.BorderSide(1, ft.Colors.GREY_700),
                            bottom=ft.BorderSide(1, ft.Colors.GREY_700),
                        ),
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

    def _confirm_clear_data(self, e=None):
        dlg = ft.AlertDialog(
            title=ft.Text("Clear All Data"),
            content=ft.Text(
                "This will permanently delete all collected data "
                "(events, observations, sessions) and reset your device.\n\n"
                "This action cannot be undone.",
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self._dismiss_dialog(dlg)),
                ft.ElevatedButton(
                    "Delete Everything",
                    on_click=lambda e: self._handle_clear_data(dlg),
                    color=ft.Colors.RED_400,
                ),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self._page.show_dialog(dlg)

    def _dismiss_dialog(self, dlg):
        dlg.open = False
        self._page.update()

    def _handle_clear_data(self, dlg):
        dlg.open = False
        self._page.update()
        self._manager.clear_all_data()
        self._log_scroll.controls.clear()
        self._log_scroll.controls.append(
            ft.Text("All data cleared.", size=11, color=ft.Colors.RED_400),
        )
        self._status_text.value = "Data cleared — collection paused"
        self._page.update()

    def _load_log(self, e=None):
        try:
            lines = read_log_lines(MAX_VISIBLE_LINES)
            self._log_scroll.controls.clear()
            if not lines:
                self._log_scroll.controls.append(
                    ft.Text("No log file found.", size=11, font_family="monospace"),
                )
                self._status_text.value = ""
            else:
                joined = "".join(lines).rstrip("\n")
                self._log_scroll.controls.append(
                    ft.TextField(
                        value=joined,
                        multiline=True,
                        read_only=True,
                        text_style=ft.TextStyle(size=11, font_family="monospace"),
                        bgcolor=ft.Colors.TRANSPARENT,
                        border=ft.InputBorder.NONE,
                    ),
                )
                self._status_text.value = f"Showing last {len(lines)} lines"
        except Exception:
            logger.exception("Failed to load log")
            self._log_scroll.controls.clear()
            self._log_scroll.controls.append(
                ft.Text("Error loading log.", size=11, color=ft.Colors.RED_400),
            )
            self._status_text.value = "Failed to load log"
        self._page.update()

    def _copy_log(self, e=None):
        lines = read_log_lines(MAX_VISIBLE_LINES)
        text = "".join(lines)
        if text:
            try:
                ft.Clipboard().set(text)
            except Exception:
                logger.exception("Failed to copy to clipboard")
                self._status_text.value = "Failed to copy"
            else:
                self._status_text.value = "Copied to clipboard"
            self._page.update()

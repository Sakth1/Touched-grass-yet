import logging

import flet as ft

from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Analytics(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Analytics"
        self.content = ft.Container(
                    content=ft.Text("Analytics"), alignment=ft.Alignment.CENTER
                )
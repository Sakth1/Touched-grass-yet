import logging

import flet as ft

from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Dashboard(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Dashboard"
        self.content = ft.Container(
            content=ft.Text("Dashboard"), alignment=ft.Alignment.CENTER
        )

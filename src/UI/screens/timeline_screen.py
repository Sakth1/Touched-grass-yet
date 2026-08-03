import logging

import flet as ft

from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Timeline(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Timeline"
        self.content = ft.Row(ft.Text("Timeline", color=ft.Colors.WHITE), alignment=ft.Alignment.CENTER)

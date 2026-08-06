import logging

import flet as ft

from core.update_checker import UpdateChecker
from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Settings"
        self.content = ft.Container(
            content=ft.Text("Settings"), alignment=ft.Alignment.CENTER
        )
        self.update_checker = UpdateChecker()

import logging

import flet as ft

from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Settings"
        self.content = ft.Text("Settings")

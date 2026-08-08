import logging

import flet as ft

from UI.screens.base_screen import BaseScreen
from UI.screens.settings import AppInfo, General
from utils.models import NavigationDestination

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(self):
        super().__init__(secondary_options=True)
        self.title = "Settings"
        self.app_info_section = AppInfo()
        self.general_section = General()
        self.content = ft.Container(content=ft.Text("Settings"))

    def _get_secondary_options(self) -> list[NavigationDestination]:
        return [
            NavigationDestination(
                label="General",
                icon=ft.Icons.SETTINGS,
                route="/settings/general",
                view=self.general_section,
            ),
            NavigationDestination(
                label="App Info",
                icon=ft.Icons.INFO,
                route="/settings/app-info",
                view=self.app_info_section,
            ),
        ]

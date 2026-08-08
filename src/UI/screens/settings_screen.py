import logging
from typing import Any

import flet as ft

from UI.screens.base_screen import BaseScreen
from UI.screens.settings import AppInfo, DataDiagnostics, General
from utils.models import NavigationDestination

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(
        self,
        config: Any = None,
        collection_manager: Any = None,
        page: ft.Page | None = None,
    ):
        super().__init__(secondary_options=True)
        self.title = "Settings"
        self.general_section = General(
            config=config, collection_manager=collection_manager, page=page
        )
        self.data_section = DataDiagnostics(
            config=config, collection_manager=collection_manager, page=page
        )
        self.app_info_section = AppInfo(config=config, page=page)
        self.content = self.general_section

    def _get_secondary_options(self) -> list[NavigationDestination]:
        return [
            NavigationDestination(
                label="General",
                icon=ft.Icons.SETTINGS,
                route="/settings/general",
                view=self.general_section,
            ),
            NavigationDestination(
                label="Data",
                icon=ft.Icons.STORAGE,
                route="/settings/data",
                view=self.data_section,
            ),
            NavigationDestination(
                label="App Info",
                icon=ft.Icons.INFO,
                route="/settings/app-info",
                view=self.app_info_section,
            ),
        ]

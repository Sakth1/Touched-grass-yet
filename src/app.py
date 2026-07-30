import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from UI.dialogs import show_permission_dialog
from UI.screens.dashboard_screen import Dashboard
from utils.models import SystemType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Touched Grass Yet"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.width = 500
        self.page.window.height = 600

        setup_file_logging()

        self.collection_manager = CollectionManager()
        self.dashboard_page = Dashboard()
        self.page.update()

        self._initiate()

    def _initiate(self):
        if (
            self.collection_manager.config.auto_start_enabled
            and not is_auto_start_enabled()
        ):
            enable_auto_start()

        if self.collection_manager.detect_platform() == SystemType.ANDROID:
            from core.collectors.android.usage_stats import check_usage_stats_permission

            if not check_usage_stats_permission():
                show_permission_dialog(self.page)


async def entrypoint(page: ft.Page):
    App(page)

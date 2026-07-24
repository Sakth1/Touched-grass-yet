import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.logging_setup import setup_file_logging
from UI.home_page import HomePage
from utils.models import SystemType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def entrypoint(page: ft.Page):
    page.title = "Touched Grass Yet"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 500
    page.window.height = 600

    setup_file_logging()

    manager = CollectionManager()
    home = HomePage(page, manager)
    page.update()

    if manager.detect_platform() == SystemType.ANDROID:
        from core.collectors.android.usage_stats import check_usage_stats_permission

        if not check_usage_stats_permission():
            await home.show_permission_dialog()

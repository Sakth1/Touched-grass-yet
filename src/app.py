import logging

import flet as ft
import asyncio

from core.application.collection_manager import CollectionManager
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from UI.dialogs import show_permission_dialog
from UI.layout_manager import app_layout_resolver
from UI.screens.dashboard_screen import Dashboard
from utils.models import AppLayout, OSType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


class App:
    def __init__(self, page: ft.Page):
        self.page = page
        self.page.title = "Unscreen"
        self.page.theme_mode = ft.ThemeMode.SYSTEM

        self._schedule_maximize() # REMOVE THIS BS OF A CODE WHEN flet #6101 IS FIXED

        setup_file_logging()

        self.collection_manager = CollectionManager()
        self.dashboard_page = Dashboard()

        self.content = ft.Container(expand=True, content=self.dashboard_page)

        self.page.views.append(self.content)
        self.page.update()

        self._initiate()

    def _schedule_maximize(self):
            if self.page.platform.is_desktop():
                self.page.run_task(self._maximize_after_delay, self.page)

    async def _maximize_after_delay(self, page: ft.Page):
        await asyncio.sleep(0.1)          # flet#6101: client window-state init must settle first
        page.window.maximized = True
        page.update(page.window)

    def _initiate(self):
        if (
            self.collection_manager.config.auto_start_enabled
            and not is_auto_start_enabled()
        ):
            enable_auto_start()

        if self.collection_manager.detect_platform() == OSType.ANDROID:
            from core.collectors.android.usage_stats import check_usage_stats_permission

            if not check_usage_stats_permission():
                show_permission_dialog(self.page)

        self.layout: AppLayout = app_layout_resolver(self.page.width, self.page.height)
        self._apply_layout(self.layout)

    def _apply_layout(self, layout: AppLayout):
        print(f"Applying layout: {layout}")
        self.page.width = layout.width
        self.page.height = layout.height
        self.page.update()


async def entrypoint(page: ft.Page):
    App(page)

import asyncio
import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from UI.dialogs import show_permission_dialog
from UI.layout_manager import app_layout_resolver
from UI.routing import RouteManager
from UI.screens.analytics_screen import Analytics
from UI.screens.dashboard_screen import Dashboard
from UI.screens.settings_screen import Settings
from UI.screens.timeline_screen import Timeline
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

        self._schedule_maximize()  # REMOVE THIS BS OF A CODE WHEN flet #6101 IS FIXED

        setup_file_logging()

        self.collection_manager = CollectionManager()
        self.dashboard_page = Dashboard()
        self.timeline_page = Timeline()
        self.analytics_page = Analytics()
        self.settings_page = Settings()

        self.container = ft.Container(expand=True)

        route_to_index = {
            "/dashboard": 0,
            "/timeline": 1,
            "/analytics": 2,
            "/settings": 3,
        }

        route_views = {
            "/dashboard": self.dashboard_page,
            "/timeline": self.timeline_page,
            "/analytics": self.analytics_page,
            "/settings": self.settings_page,
        }

        self.route_manager = RouteManager(
            page=self.page,
            container=self.container,
            route_views=route_views,
            route_to_index=route_to_index,
        )

        self.page.navigation_bar = ft.NavigationBar(
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.DASHBOARD, label="Dashboard"
                ),
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.TIMELINE, label="Timeline"
                ),
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.ANALYTICS, label="Analytics"
                ),
                ft.NavigationBarDestination(
                    icon=ft.icons.Icons.SETTINGS, label="Settings"
                ),
            ],
            on_change=self._handle_navigation_change,
        )

        self.page.on_route_change = self.route_manager.handle_route_change

        self._initiate()

    def _schedule_maximize(self):
        if self.page.platform is not None and self.page.platform.is_desktop() is True:
            self.page.run_task(self._maximize_after_delay)

    async def _maximize_after_delay(self):
        await asyncio.sleep(
            0.1
        )  # flet#6101: client window-state init must settle first
        self.page.window.maximized = True
        self.page.update()

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

        width = self.page.window.width if self.page.window.width is not None else 500
        height = self.page.window.height if self.page.window.height is not None else 600

        self.layout: AppLayout = app_layout_resolver(width, height)
        self._apply_layout(self.layout)

    def _apply_layout(self, layout: AppLayout):
        print(f"Applying layout: {layout}")
        self.page.width = layout.width
        self.page.height = layout.height
        self.page.update()

    def _handle_navigation_change(self, event):
        self.route_manager.handle_navigation_change(event)


async def entrypoint(page: ft.Page):
    App(page)

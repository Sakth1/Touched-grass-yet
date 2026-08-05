import asyncio
import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from core.state.app_state import get_app_state
from UI.custom.navigation_bar import (
    CustomNavigationBar,
    CustomNavigationBarDestination,
)
from UI.custom.navigation_drawer import (
    CustomNavigationDrawer,
    CustomNavigationDrawerDestination,
)
from UI.dialogs import show_permission_dialog
from UI.routing import RouteManager
from UI.screens.analytics_screen import Analytics
from UI.screens.dashboard_screen import Dashboard
from UI.screens.settings_screen import Settings
from UI.screens.timeline_screen import Timeline
from utils.constants import (
    ASSET_DIR,
    DEFAULT_PAGE_HEIGHT,
    DEFAULT_PAGE_WIDTH,
    MIN_PAGE_HEIGHT,
    MIN_PAGE_WIDTH,
)
from utils.layout import app_layout_resolver
from utils.models import AppLayout, OSType, ScreenFormFactor
from utils.platform import detect_os

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
        self._set_window_icon()

        self._schedule_maximize()  # REMOVE THIS BS OF A CODE WHEN flet #6101 IS FIXED

        setup_file_logging()

        self.collection_manager = CollectionManager()

        self.dashboard_page = Dashboard()
        self.timeline_page = Timeline()
        self.analytics_page = Analytics()
        self.settings_page = Settings()

        self.dashboard_view = ft.Container(
            content=ft.ResponsiveRow([self.dashboard_page])
        )
        self.content_container = ft.Container(expand=True)

        self.navigation_rail = None
        self.shell = ft.Row(expand=True, controls=[self.content_container])

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
            container=self.content_container,
            route_views=route_views,
            route_to_index=route_to_index,
        )

        self.page.on_resize = self._handle_page_resize
        self.page.add(self.shell)

        self._initiate()

    def _set_window_icon(self) -> None:
        if self.page.platform is not None and self.page.platform.is_desktop():
            icon = ASSET_DIR / "icon_windows.ico"
            if icon.exists():
                self.page.window.icon = str(icon)

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

        if detect_os() == OSType.ANDROID:
            from core.collectors.android.usage_stats import check_usage_stats_permission

            if not check_usage_stats_permission():
                show_permission_dialog(self.page)

        width = (
            self.page.window.width
            if self.page.window.width is not None
            else DEFAULT_PAGE_WIDTH
        )
        height = (
            self.page.window.height
            if self.page.window.height is not None
            else DEFAULT_PAGE_HEIGHT
        )

        self.layout: AppLayout = app_layout_resolver(width, height)
        self._apply_layout(self.layout)

    def _handle_page_resize(self, _event):
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        page_width, page_height = self._resolve_page_dimensions()
        self.layout = app_layout_resolver(page_width, page_height)
        self._apply_layout(self.layout)

    def _apply_layout(self, layout: AppLayout):
        self.page.width = layout.width
        self.page.height = layout.height
        get_app_state().set_layout(layout)

        match layout.screen_form_factor:
            case ScreenFormFactor.MOBILE | ScreenFormFactor.TABLET:
                # NOTE: see how float nav bar still works when assigned to page.navbar even tho it is not a navbar class
                self._ensure_navigation_bar()
                self.shell.controls = [self.content_container]

            case ScreenFormFactor.DESKTOP:
                self.page.navigation_bar = None
                self.shell.controls = [
                    self._ensure_rail(extended=True),
                    self.content_container,
                ]

            case _:
                raise NotImplementedError

        self.page.update()

    def _resolve_page_dimensions(self) -> tuple[float, float]:
        page_width = getattr(self.page, "width", 0) or DEFAULT_PAGE_WIDTH
        page_height = getattr(self.page, "height", 0) or DEFAULT_PAGE_HEIGHT
        media = getattr(self.page, "media", None)
        padding = getattr(media, "padding", None)
        if padding is not None:
            page_width = max(
                MIN_PAGE_WIDTH,
                page_width
                - (getattr(padding, "left", 0) or 0)
                - (getattr(padding, "right", 0) or 0),
            )
            page_height = max(
                MIN_PAGE_HEIGHT,
                page_height
                - (getattr(padding, "top", 0) or 0)
                - (getattr(padding, "bottom", 0) or 0),
            )
        if getattr(self.page, "navigation_bar", None) is not None:
            page_height = max(
                MIN_PAGE_HEIGHT,
                page_height - (getattr(self.page.navigation_bar, "height", 0) or 0),
            )
        return page_width, page_height

    def _ensure_navigation_bar(self):
        self.page.navigation_bar = CustomNavigationBar(
            destinations=[
                CustomNavigationBarDestination(
                    icon=ft.icons.Icons.DASHBOARD,
                    label="Dashboard",
                    selected=True,
                ),
                CustomNavigationBarDestination(
                    icon=ft.icons.Icons.TIMELINE,
                    label="Timeline",
                    selected=False,
                ),
                CustomNavigationBarDestination(
                    icon=ft.icons.Icons.ANALYTICS,
                    label="Analytics",
                    selected=False,
                ),
                CustomNavigationBarDestination(
                    icon=ft.icons.Icons.SETTINGS,
                    label="Settings",
                    selected=False,
                ),
            ],
            selected_index=0,
            adaptive=True,
            label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
            on_change=self._handle_navigation_change,
        )
        self.page.on_route_change = self.route_manager.handle_route_change

    def _ensure_rail(self, extended: bool) -> CustomNavigationDrawer:
        if self.navigation_rail is not None:
            return self.navigation_rail

        self.navigation_rail = CustomNavigationDrawer(
            trailing=CustomNavigationDrawerDestination(
                icon=ft.icons.Icons.SETTINGS_OUTLINED,
                label="Settings",
                tooltip="Settings",
                on_click=self._handle_settings_navigation,
            ),
            destinations=[
                CustomNavigationDrawerDestination(
                    icon=ft.icons.Icons.DASHBOARD, label="Dashboard"
                ),
                CustomNavigationDrawerDestination(
                    icon=ft.icons.Icons.TIMELINE, label="Timeline"
                ),
                CustomNavigationDrawerDestination(
                    icon=ft.icons.Icons.ANALYTICS, label="Analytics"
                ),
            ],
            selected_index=0,
            extended=extended,
            on_change=self._handle_navigation_change,
        )
        return self.navigation_rail

    def _handle_settings_navigation(self, _event) -> None:
        self.route_manager.navigate("/settings")

    def _handle_navigation_change(self, event: ft.ControlEvent):
        self.route_manager.handle_navigation_change(event)


async def entrypoint(page: ft.Page):
    App(page)

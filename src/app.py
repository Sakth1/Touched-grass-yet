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
from UI.custom.secondary_navigation_panel import (
    SecondaryNavigationDestination,
    SecondaryNavigationPanel,
)
from UI.dialogs import show_permission_dialog
from UI.layout.layout_resolver import app_layout_resolver
from UI.routing import RouteManager
from UI.screens.analytics_screen import Analytics
from UI.screens.base_screen import BaseScreen
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
from utils.models import (
    AppLayout,
    NavigationDestination,
    NavigationPattern,
    OSType,
    SecondaryNavigationPattern,
)
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

        self.content_container = ft.Container(expand=True)

        self.navigation_rail = None
        self.secondary_navigation_panel = None
        self._panel_view = None
        self.current_view: BaseScreen = None
        self.populated_options_inline = False
        self.shell = ft.Row(expand=True, controls=[self.content_container])

        self.section_routes: dict[str, list[str]] = {
            "/settings": ["/settings/general", "/settings/app-info"],
        }

        self.destinations = [
            NavigationDestination(
                "/dashboard",
                "Dashboard",
                ft.Icons.DASHBOARD,
                self.dashboard_page,
            ),
            NavigationDestination(
                "/timeline",
                "Timeline",
                ft.Icons.TIMELINE,
                self.timeline_page,
            ),
            NavigationDestination(
                "/analytics",
                "Analytics",
                ft.Icons.ANALYTICS,
                self.analytics_page,
            ),
            NavigationDestination(
                "/settings",
                "Settings",
                ft.Icons.SETTINGS,
                self.settings_page,
            ),
        ]

        self.route_manager = RouteManager(
            page=self.page,
            container=self.content_container,
            destinations=self.destinations,
            section_routes=self.section_routes,
        )

        self.page.on_route_change = self.route_manager.handle_route_change
        self.page.on_resize = self._handle_page_resize
        self.page.on_media_change = self._handle_media_change
        self.page.add(self.shell)

        self._initiate()
        self.route_manager.navigate(self.route_manager.current_route)

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

        self.layout: AppLayout = app_layout_resolver(
            width, height, media=getattr(self.page, "media", None)
        )
        self._apply_layout(self.layout)

    def _handle_page_resize(self, _event):
        self._apply_responsive_layout()

    def _handle_media_change(self, _event):
        self._apply_responsive_layout()

    def _apply_responsive_layout(self):
        page_width, page_height = self._resolve_page_dimensions()
        layout = app_layout_resolver(
            page_width, page_height, media=getattr(self.page, "media", None)
        )
        if self.layout is not None and layout == self.layout:
            return
        self.layout = layout
        self._apply_layout(layout)

    def _apply_layout(self, layout: AppLayout):
        self.page.width = layout.width
        self.page.height = layout.height
        get_app_state().set_layout(layout)

        self._update_layout()

    def _update_layout(self):
        match self.layout.navigation:
            case NavigationPattern.BOTTOM_BAR:
                nav = self._ensure_navigation_bar()
                nav.apply_layout(self.layout)
                self.shell.controls = [self.content_container]

            case NavigationPattern.MINI_RAIL:
                self.page.navigation_bar = None
                self._ensure_rail(extended=False).apply_layout(self.layout)
                self._build_secondary_options(self.layout)

                self.shell.controls = [self.navigation_rail]
                self._append_secondary_panel()

            case NavigationPattern.EXTENDED_RAIL:
                self.page.navigation_bar = None
                self._ensure_rail(extended=True).apply_layout(self.layout)
                self._build_secondary_options(self.layout)

                self.shell.controls = [self.navigation_rail]
                self._append_secondary_panel()

            case _:
                raise NotImplementedError

        self._apply_content_padding(self.layout)
        self.page.update()

    def _append_secondary_panel(self) -> None:
        """Place the secondary side panel in the shell when it applies.

        The panel is only relevant for side-panel form factors; inline
        layouts (phones, tablet portrait) render the secondary sections
        inside the content area, so a leftover panel must not take space.
        """
        if (
            self.secondary_navigation_panel is not None
            and self.layout.secondary_navigation
            is SecondaryNavigationPattern.SIDE_PANEL
        ):
            self.secondary_navigation_panel.apply_layout(self.layout)
            self.shell.controls.append(self.secondary_navigation_panel)
        self.shell.controls.append(self.content_container)

    def _build_secondary_options(self, layout: AppLayout):
        match layout.secondary_navigation:
            case SecondaryNavigationPattern.INLINE:
                self._populate_page_with_options()
                self.populated_options_inline = True
            case SecondaryNavigationPattern.SIDE_PANEL:
                if self.populated_options_inline:
                    ...
                self._ensure_secondary_panel()
                self.populated_options_inline = False
            case _:
                raise NotImplementedError

    def _populate_page_with_options(self): ...

    def _ensure_secondary_panel(self):
        self.current_view = self.route_manager.view_for(
            self.route_manager.current_route
        )
        has_options = self.current_view is not None and getattr(
            self.current_view, "_secondary_options", False
        )
        if not has_options:
            self.secondary_navigation_panel = None
            self._panel_view = None
            return

        # Reuse the panel while the same view owns it so window resizes do
        # not wipe the current section selection.
        if (
            self.secondary_navigation_panel is not None
            and self._panel_view is self.current_view
        ):
            self.secondary_navigation_panel.apply_layout(self.layout)
            return

        self.secondary_destination: list[NavigationDestination] = (
            self.current_view._get_secondary_options()
        )

        self.secondary_navigation_panel = SecondaryNavigationPanel(
            destinations=[
                SecondaryNavigationDestination(
                    icon=dest.icon,
                    label=dest.label,
                    selected=i == 0,
                )
                for i, dest in enumerate(self.secondary_destination)
            ],
            selected_index=0,
            adaptive=True,
        )
        self.secondary_navigation_panel.apply_layout(self.layout)
        self._panel_view = self.current_view

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

    def _apply_content_padding(self, layout: AppLayout) -> None:
        """Pad the content area with design spacing plus system safe insets.

        The floating bottom bar already clears the gesture area on its own,
        so with a bottom bar the content does not need the extra bottom inset.
        """
        base = layout.padding
        safe_left, safe_top, safe_right, safe_bottom = layout.safe_padding
        bottom_bar = layout.navigation is NavigationPattern.BOTTOM_BAR
        self.content_container.padding = ft.padding.Padding.only(
            left=base + safe_left,
            top=base + safe_top,
            right=base + safe_right,
            bottom=base + (0.0 if bottom_bar else safe_bottom),
        )

    def _ensure_navigation_bar(self):
        self.page.navigation_bar = CustomNavigationBar(
            destinations=[
                CustomNavigationBarDestination(
                    icon=dest.icon,
                    label=dest.label,
                    selected=i == 0,
                )
                for i, dest in enumerate(self.destinations)
            ],
            selected_index=0,
            adaptive=True,
            label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
            on_change=self._handle_navigation_change,
        )
        return self.page.navigation_bar

    def _ensure_rail(self, extended: bool) -> CustomNavigationDrawer:
        if self.navigation_rail is not None:
            return self.navigation_rail

        settings = next(d for d in self.destinations if d.route == "/settings")
        main = [d for d in self.destinations if d.route != "/settings"]

        self.navigation_rail = CustomNavigationDrawer(
            trailing=CustomNavigationDrawerDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                label=settings.label,
                tooltip=settings.label,
            ),
            destinations=[
                CustomNavigationDrawerDestination(
                    icon=dest.icon,
                    label=dest.label,
                    tooltip=dest.label,
                )
                for dest in main
            ],
            selected_index=0,
            extended=extended,
            on_change=self._handle_navigation_change,
        )
        return self.navigation_rail

    def _handle_navigation_change(self, event: ft.ControlEvent):
        self.route_manager.handle_navigation_change(event)
        self._update_layout()


async def entrypoint(page: ft.Page):
    App(page)

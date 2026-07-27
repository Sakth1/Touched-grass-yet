import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from UI.home_page import HomePage
from UI.layouts.responsive_scaffold import ResponsiveScaffold
from UI.screens.about_screen import AboutScreen
from UI.screens.export_screen import ExportScreen
from UI.screens.settings_screen import SettingsScreen
from UI.screens.timeline_screen import TimelineScreen
from UI.services.router import Router
from UI.state.app_state import AppState
from UI.theme.app_theme import build_dark_theme
from utils.models import SystemType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def entrypoint(page: ft.Page):
    page.title = "Touched Grass Yet"
    page.theme = build_dark_theme()
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0

    setup_file_logging()

    manager = CollectionManager()
    state = AppState()

    scaffold = ResponsiveScaffold(page, state)
    router = Router(page, state, scaffold)

    home = HomePage(page, manager)

    def build_dashboard():
        return home.build_content()

    router.register("/", build_dashboard)
    router.register("/timeline", lambda: TimelineScreen())
    router.register("/export", lambda: ExportScreen())
    router.register("/settings", lambda: SettingsScreen())
    router.register("/about", lambda: AboutScreen())

    page.go("/")

    if manager.config.auto_start_enabled and not is_auto_start_enabled():
        enable_auto_start()

    if manager.detect_platform() == SystemType.ANDROID:
        from core.collectors.android.usage_stats import check_usage_stats_permission

        if not check_usage_stats_permission():
            await home.show_permission_dialog()

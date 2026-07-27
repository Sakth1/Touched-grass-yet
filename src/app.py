import logging

import flet as ft

from core.application.collection_manager import CollectionManager
from core.application.data_bridge import DataBridge
from core.auto_start import enable as enable_auto_start
from core.auto_start import is_enabled as is_auto_start_enabled
from core.logging_setup import setup_file_logging
from UI.layouts.app_shell import AppShell
from UI.layouts.content_area import ContentArea
from UI.screens.analytics_screen import AnalyticsScreen
from UI.screens.dashboard_screen import DashboardScreen
from UI.screens.settings_screen import SettingsScreen
from UI.screens.timeline_screen import TimelineScreen
from UI.services.command_registry import CommandRegistry
from UI.services.state import AppState, Destination, ThemeMode
from UI.theme.app_theme import build_theme
from utils.models import SystemType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


def _apply_theme(page: ft.Page, state: AppState) -> None:
    seed = state.seed_color_name
    mode = state.theme_mode
    page.theme = build_theme(seed, dark=False)
    page.dark_theme = build_theme(seed, dark=True)
    mode_map = {
        ThemeMode.SYSTEM: ft.ThemeMode.SYSTEM,
        ThemeMode.LIGHT: ft.ThemeMode.LIGHT,
        ThemeMode.DARK: ft.ThemeMode.DARK,
    }
    page.theme_mode = mode_map.get(mode, ft.ThemeMode.SYSTEM)
    page.update()


async def entrypoint(page: ft.Page) -> None:
    page.title = "Touched Grass Yet"
    page.padding = 0

    setup_file_logging()

    manager = CollectionManager()
    state = AppState()
    registry = CommandRegistry()

    _apply_theme(page, state)

    content_area = ContentArea(state)
    screens = [
        DashboardScreen(state),
        TimelineScreen(state),
        AnalyticsScreen(state),
        SettingsScreen(state),
    ]
    for dest, screen in zip(Destination, screens, strict=True):
        content_area.register_screen(dest, screen)

    shell = AppShell(page, state, registry, content_area)
    page.add(shell)

    content_area.navigate_to(Destination.DASHBOARD)

    state.subscribe("seed_color", lambda: _apply_theme(page, state))
    state.subscribe("theme_mode", lambda: _apply_theme(page, state))

    if manager.config.auto_start_enabled and not is_auto_start_enabled():
        enable_auto_start()

    if manager.detect_platform() == SystemType.ANDROID:
        from core.collectors.android.usage_stats import check_usage_stats_permission
        if not check_usage_stats_permission():
            ...

    bridge = DataBridge(manager, state)
    await manager.start()
    await bridge.start()

    async def _on_disconnect(_e) -> None:
        await bridge.stop()
        await manager.stop()

    page.on_disconnect = _on_disconnect

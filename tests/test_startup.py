"""Startup smoke tests — verify the entire UI tree can be constructed.

Layer 5 in the validation architecture:
catches construction-time exceptions before runtime.
"""

from unittest.mock import MagicMock

import flet as ft
import pytest

from UI.layouts.app_shell import AppShell
from UI.layouts.content_area import ContentArea
from UI.screens.analytics_screen import AnalyticsScreen
from UI.screens.dashboard_screen import DashboardScreen
from UI.screens.settings_screen import SettingsScreen
from UI.screens.timeline_screen import TimelineScreen
from UI.services.command_registry import CommandRegistry
from UI.services.state import AppState, Destination


class TestCoreServicesConstruct:
    """Layer 3/4: pure-Python wiring constructs without error."""

    def test_app_state_constructs(self) -> None:
        state = AppState()
        assert state.collection_status is not None
        assert state.today_seconds == 0.0

    def test_command_registry_constructs(self) -> None:
        registry = CommandRegistry()
        assert registry is not None

    def test_content_area_constructs(self) -> None:
        state = AppState()
        ca = ContentArea(state)
        assert isinstance(ca, ft.Container)


class TestScreensConstruct:
    """Every screen constructs and builds content without error."""

    @pytest.fixture
    def state(self) -> AppState:
        return AppState()

    def test_dashboard_screen(self, state: AppState) -> None:
        screen = DashboardScreen(state)
        result = screen.build_content()
        assert isinstance(result, ft.Container)

    def test_timeline_screen(self, state: AppState) -> None:
        screen = TimelineScreen(state)
        result = screen.build_content()
        assert isinstance(result, ft.Container)

    def test_analytics_screen(self, state: AppState) -> None:
        screen = AnalyticsScreen(state)
        result = screen.build_content()
        assert isinstance(result, ft.Container)

    def test_settings_screen(self, state: AppState) -> None:
        screen = SettingsScreen(state)
        result = screen.build_content()
        assert isinstance(result, ft.Container)

    def test_screens_register_in_content_area(self, state: AppState) -> None:
        ca = ContentArea(state)
        screens = [
            DashboardScreen(state),
            TimelineScreen(state),
            AnalyticsScreen(state),
            SettingsScreen(state),
        ]
        for dest, screen in zip(Destination, screens, strict=True):
            ca.register_screen(dest, screen)
        assert len(ca._screens) == 4


class TestAppShellConstructs:
    """The full shell — constructs the entire UI tree transitively.

    If any component (CommandPalette, StatusBar, Sidebar, etc.)
    raises during __init__, this test fails.
    """

    @pytest.fixture
    def mock_page(self) -> MagicMock:
        page = MagicMock(spec=ft.Page)
        page.width = 1200
        page.height = 800
        # AnimatedSwitcherTransition needs to be accessible
        page.theme_mode = ft.ThemeMode.SYSTEM
        return page

    @pytest.fixture
    def state(self) -> AppState:
        return AppState()

    @pytest.fixture
    def registry(self) -> CommandRegistry:
        return CommandRegistry()

    @pytest.fixture
    def content_area(self, state: AppState) -> ContentArea:
        ca = ContentArea(state)
        screens = [
            DashboardScreen(state),
            TimelineScreen(state),
            AnalyticsScreen(state),
            SettingsScreen(state),
        ]
        for dest, screen in zip(Destination, screens, strict=True):
            ca.register_screen(dest, screen)
        return ca

    def test_app_shell_constructs(
        self,
        mock_page: MagicMock,
        state: AppState,
        registry: CommandRegistry,
        content_area: ContentArea,
    ) -> None:
        shell = AppShell(mock_page, state, registry, content_area)
        assert isinstance(shell, ft.Container)

    def test_command_palette_has_on_dismiss(
        self,
        mock_page: MagicMock,
        state: AppState,
        registry: CommandRegistry,
    ) -> None:
        from UI.layouts.command_palette import CommandPalette

        cp = CommandPalette(mock_page, state, registry)
        assert hasattr(cp, "_on_dismiss")

    def test_command_palette_registers_commands(
        self,
        mock_page: MagicMock,
        state: AppState,
        registry: CommandRegistry,
    ) -> None:
        from UI.layouts.command_palette import CommandPalette

        CommandPalette(mock_page, state, registry)
        # The 4 common commands should be registered during __init__
        results = registry.search("")
        assert len(results) >= 4

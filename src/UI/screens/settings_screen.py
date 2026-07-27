import flet as ft

from ..components.section_list import SettingsSection, SettingsTile
from ..services.state import AppState, ThemeMode
from ..theme.tokens import SEED_COLORS, SPACING
from .base_screen import BaseScreen

_COLOR_OPTIONS = list(SEED_COLORS.keys())


class SettingsScreen(BaseScreen):
    def __init__(self, state: AppState) -> None:
        super().__init__(state)

        self._foreground_switch = ft.Switch(value=True, on_change=self._on_setting_change)
        self._afk_switch = ft.Switch(value=True, on_change=self._on_setting_change)
        self._power_switch = ft.Switch(value=True, on_change=self._on_setting_change)
        self._url_switch = ft.Switch(value=False, on_change=self._on_setting_change)

        theme_options = [
            ft.dropdown.Option("System"),
            ft.dropdown.Option("Light"),
            ft.dropdown.Option("Dark"),
        ]
        self._theme_dropdown = ft.Dropdown(
            value="System",
            options=theme_options,
            width=160,
        )
        self._theme_dropdown.on_change = self._on_theme_change

        self._color_dropdown = ft.Dropdown(
            value="purple",
            options=[ft.dropdown.Option(c) for c in _COLOR_OPTIONS],
            width=160,
        )
        self._color_dropdown.on_change = self._on_color_change

        self._version_label = ft.Text("v0.4.1", size=14)
        self._platform_label = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self._db_size_label = ft.Text("2.3 MB", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

    def build_content(self) -> ft.Control:
        import platform as _platform
        self._platform_label.value = _platform.system() + " " + _platform.release()

        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Text("Settings", size=24, weight=ft.FontWeight.W_600),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
                ft.Container(
                    content=SettingsSection(
                        title="Collection",
                        controls=[
                            SettingsTile("Foreground Tracking", subtitle="Active app detection",
                                        trailing=self._foreground_switch),
                            SettingsTile("AFK Detection", trailing=self._afk_switch),
                            SettingsTile("Power Monitoring", subtitle="Battery level tracking",
                                        trailing=self._power_switch),
                            SettingsTile("URL Extraction", subtitle="Extract URLs from browser titles",
                                        trailing=self._url_switch),
                        ],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=SettingsSection(
                        title="Appearance",
                        controls=[
                            SettingsTile(
                                "Theme",
                                trailing=self._theme_dropdown,
                            ),
                            SettingsTile(
                                "Accent Color",
                                subtitle="Material Design 3 seed color",
                                trailing=self._color_dropdown,
                            ),
                        ],
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
                ft.Container(
                    content=SettingsSection(
                        title="Privacy",
                        description="All data is stored locally. No telemetry, no cloud,"
                                    " no collection without your consent.",
                        controls=[
                            ft.Container(
                                content=ft.TextButton(
                                    "Clear All Data",
                                    icon=ft.Icons.DELETE_FOREVER,
                                    style=ft.ButtonStyle(color=ft.Colors.ERROR),
                                    on_click=self._confirm_clear_data,
                                ),
                                padding=ft.padding.Padding.only(top=SPACING["sm"]),
                            ),
                        ],
                    ),
                    padding=ft.padding.Padding.symmetric(horizontal=SPACING["lg"]),
                ),
                ft.Container(
                    content=SettingsSection(
                        title="About",
                        controls=[
                            SettingsTile("Version", trailing=self._version_label),
                            SettingsTile("Platform", trailing=self._platform_label),
                            SettingsTile("Database Size", trailing=self._db_size_label),
                            SettingsTile("Source Code", subtitle="github.com/Sakth1/Touched-grass-yet"),
                            ft.Container(
                                content=ft.TextButton(
                                    "Check for Updates",
                                    icon=ft.Icons.UPDATE,
                                    on_click=lambda _: self.state.context_content and None,
                                ),
                                padding=ft.padding.Padding.only(top=SPACING["sm"]),
                            ),
                        ],
                    ),
                    padding=ft.padding.Padding.all(SPACING["lg"]),
                ),
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
        )
        self.content = content
        return self

    def _on_setting_change(self, e: ft.ControlEvent) -> None:
        pass

    def _on_theme_change(self, e: ft.ControlEvent) -> None:
        theme_map = {
            "System": ThemeMode.SYSTEM,
            "Light": ThemeMode.LIGHT,
            "Dark": ThemeMode.DARK,
        }
        self.state.theme_mode = theme_map.get(e.control.value, ThemeMode.SYSTEM)

    def _on_color_change(self, e: ft.ControlEvent) -> None:
        self.state.seed_color_name = e.control.value

    def _confirm_clear_data(self, e: ft.ControlEvent) -> None:
        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Clear All Data"),
            content=ft.Text("This will permanently delete all collected data. This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: self._close_dialog(dlg)),
                ft.TextButton("Clear", style=ft.ButtonStyle(color=ft.Colors.ERROR),
                              on_click=lambda _: self._do_clear_data(dlg)),
            ],
        )
        if hasattr(self, "page"):
            self.page.show_dialog(dlg)
            self.page.update()

    def _close_dialog(self, dlg: ft.AlertDialog) -> None:
        dlg.open = False
        if hasattr(self, "page"):
            self.page.update()

    def _do_clear_data(self, dlg: ft.AlertDialog) -> None:
        dlg.open = False
        if hasattr(self, "page"):
            self.page.update()






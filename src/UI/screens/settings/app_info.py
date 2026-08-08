import asyncio
import logging

import flet as ft

from core.config_manager import ConfigManager
from core.update_checker import UpdateChecker, UpdateCheckError
from UI.dialogs import show_alert_dialog
from UI.screens.settings.settings_card import SettingsCard
from utils.constants import RELEASES_PAGE_URL
from utils.flet_helpers import show_snack_bar
from utils.paths import get_data_dir

logger = logging.getLogger(__name__)


def _info_row(label: str, value: str) -> ft.Row:
    return ft.Row(
        controls=[
            ft.Text(label, width=160),
            ft.Text(value, selectable=True),
        ],
    )


class AppInfo(ft.Container):
    """App information section rendered under ``/settings/app-info``."""

    def __init__(
        self,
        config: ConfigManager,
        page: ft.Page | None = None,
    ):
        super().__init__()
        self._config = config or ConfigManager()
        self._page = page
        self._update_checker = UpdateChecker()
        self._checking = False

        from core import device_identity
        from utils.platform import detect_os
        from utils.versions import get_current_version

        self._version = get_current_version()
        self._platform = detect_os().name.lower()
        self._device_id = device_identity.get_device_id()
        self._data_dir = get_data_dir()

        self._auto_update_switch = ft.Switch(
            value=self._config.auto_update_enabled,
            label="Check for updates on startup",
            on_change=self._on_auto_update_changed,
        )
        self._check_btn = ft.FilledTonalButton(
            "Check for updates",
            icon=ft.Icons.UPDATE,
            on_click=self._check_for_updates,
        )
        self._open_releases_btn = ft.OutlinedButton(
            "Open releases page",
            icon=ft.Icons.OPEN_IN_NEW,
            url=RELEASES_PAGE_URL,
        )

        self.content = ft.Column(
            spacing=16,
            controls=[
                SettingsCard(
                    "Updates",
                    [
                        ft.Text(f"Installed version: {self._version}"),
                        self._auto_update_switch,
                        ft.Row(
                            controls=[self._check_btn, self._open_releases_btn],
                            wrap=True,
                        ),
                    ],
                ),
                SettingsCard(
                    "About",
                    [
                        _info_row("Version", self._version),
                        _info_row("Platform", self._platform),
                        _info_row("Device ID", self._device_id),
                        _info_row("Data directory", self._data_dir),
                    ],
                ),
                SettingsCard(
                    "Privacy",
                    [
                        ft.Text(
                            "Unscreen is privacy-first: all collected data stays "
                            "on this device. Nothing is uploaded, no account is "
                            "required, and no analytics are collected.",
                            size=12,
                        ),
                    ],
                ),
            ],
        )

    # ── Handlers ──────────────────────────────────────────────────────────

    def _on_auto_update_changed(self, event: ft.ControlEvent) -> None:
        self._config.auto_update_enabled = bool(getattr(event.control, "value", False))
        self._config.save()
        self._toast(
            "Auto-update check "
            + ("enabled" if self._config.auto_update_enabled else "disabled")
        )

    def _check_for_updates(self, _event) -> None:
        if self._page is None or self._checking:
            return
        self._checking = True
        self._check_btn.disabled = True
        self._check_btn.text = "Checking…"
        self._toast("Checking for updates…")
        self._page.run_task(self._run_update_check)
        self._page.update()

    async def _run_update_check(self) -> None:
        page = self._page
        try:
            info = await asyncio.to_thread(self._update_checker.check_for_update)
        except UpdateCheckError as exc:
            self._toast("Update check failed")
            if page is not None:
                show_alert_dialog(page, "Update check failed", str(exc))
            return
        finally:
            self._checking = False
            if self._page is not None:
                self._check_btn.disabled = False
                self._check_btn.text = "Check for updates"
                self._page.update()

        if info is None:
            self._toast("You're up to date")
            if page is not None:
                show_alert_dialog(
                    page,
                    "Up to date",
                    f"You're running the latest version ({self._version}).",
                )
            return

        notes = (info.release_notes or "No release notes provided.").strip()
        message = (
            f"Version {info.version} is available (installed: {self._version}).\n\n"
            f"{notes[:2000]}\n\n"
            f"Open the releases page to download it."
        )
        if page is not None:
            show_alert_dialog(
                page,
                "Update available",
                message,
                button_text="Open releases page",
                on_close=lambda: page.launch_url(RELEASES_PAGE_URL),
            )

    def _toast(self, message: str) -> None:
        if self._page is not None:
            show_snack_bar(self._page, message)

    def on_sub_route(self, route: str) -> None:
        """Refresh control values when the section becomes visible."""
        self._auto_update_switch.value = self._config.auto_update_enabled
        if self.parent is not None:
            self.update()

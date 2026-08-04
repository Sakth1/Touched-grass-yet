import contextlib
import logging
from typing import Callable, Optional

import flet as ft

logger = logging.getLogger(__name__)


def show_alert_dialog(
    page: ft.Page,
    title: str,
    message: str,
    button_text: str = "OK",
    on_close: Optional[Callable[[], None]] = None,
) -> None:
    """Show a modal info dialog with a single action button."""
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title, weight=ft.FontWeight.BOLD),
        content=ft.Text(message, text_align=ft.TextAlign.CENTER),
        actions=[
            ft.TextButton(
                button_text,
                on_click=lambda _: _handle_alert_close(page, on_close),
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.CENTER,
    )
    page.show_dialog(dialog)
    safe_update(page)


def _handle_alert_close(page: ft.Page, on_close: Optional[Callable]) -> None:
    safe_pop_dialog(page)
    if on_close is not None:
        on_close()


def safe_pop_dialog(page: ft.Page) -> None:
    """Close the topmost dialog while tolerating detached-control errors."""
    with contextlib.suppress(IndexError, RuntimeError):
        page.pop_dialog()


def safe_update(control: ft.Control) -> None:
    """Update a Flet control while tolerating detached-control errors."""
    try:
        control.update()
    except RuntimeError as exc:
        logger.debug("safe_update suppressed RuntimeError: %s", exc, exc_info=True)
    except Exception as exc:
        logger.warning(
            "safe_update suppressed unexpected error: %s", exc, exc_info=True
        )


def show_permission_dialog(page: ft.Page):
    dlg = ft.AlertDialog(
        title=ft.Text("Usage Access Required"),
        content=ft.Text(
            "This app needs Usage Access permission to track "
            "which apps are in the foreground.\n\n"
            "Please enable it in:\n"
            "Settings → Apps → Special App Access → Usage Access",
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: _close_dialog(page, dlg)),
            ft.Button("Open Settings", on_click=lambda e: _open_settings(page, dlg)),
        ],
    )
    page.show_dialog(dlg)


def _close_dialog(page: ft.Page, dlg: ft.AlertDialog):
    dlg.open = False
    page.update()


def _open_settings(page: ft.Page, dlg: ft.AlertDialog):
    dlg.open = False
    page.update()
    from core.collectors.android.usage_stats import open_usage_access_settings

    open_usage_access_settings()

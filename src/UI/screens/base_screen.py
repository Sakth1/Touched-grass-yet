import logging

import flet as ft

from core.state.app_state import KEY_LAYOUT, get_app_state
from utils.models import AppLayout

logger = logging.getLogger(__name__)


class BaseScreen(ft.Container):
    def __init__(
        self,
    ):
        super().__init__()
        self._layout: AppLayout | None = None
        get_app_state().on_change(KEY_LAYOUT, self._on_layout_changed)

    def _on_layout_changed(self, _key: str) -> None:
        layout = get_app_state().layout
        if layout is not None:
            self.apply_layout(layout)

    def apply_layout(self, layout: AppLayout) -> None:
        """Apply layout-derived spacing; the shell owns page-level padding.

        Screens sit inside the padded content container, so they keep zero
        padding of their own. On wide layouts the content is capped at
        ``content_max_width`` and centered by the parent ResponsiveRow.
        """
        self._layout = layout
        self.padding = 0
        capped = layout.content_max_width > 0
        self.col = {"xs": 12, "sm": 12, "md": 12, "lg": 12} if capped else 12
        self.width = layout.content_max_width if capped else None
        if self.parent is not None:
            self.update()

    def _page_update(self):
        self.page.update()

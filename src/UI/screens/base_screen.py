import logging

import flet as ft

logger = logging.getLogger(__name__)


class BaseScreen(ft.Container):
    def __init__(
        self,
    ):
        super().__init__()

    def _page_update(self):
        self.page.update()

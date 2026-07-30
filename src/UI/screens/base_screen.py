import logging

import flet as ft

logger = logging.getLogger(__name__)


class BaseScreen(ft.Container):
    def __init__(self):
        super().__init__()
        
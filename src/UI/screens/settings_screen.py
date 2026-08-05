import logging

import flet as ft

from UI.screens.base_screen import BaseScreen
from core.update_checker import UpdateChecker

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Settings"
        self.update_checker = UpdateChecker()

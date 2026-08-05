import logging

from core.update_checker import UpdateChecker
from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Settings(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Settings"
        self.update_checker = UpdateChecker()

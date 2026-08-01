import logging

from UI.screens.base_screen import BaseScreen

logger = logging.getLogger(__name__)


class Timeline(BaseScreen):
    def __init__(self):
        super().__init__()
        self.title = "Timeline"

import flet as ft

from core.update_checker import UpdateChecker


class AppInfo(ft.Container):
    """App information section rendered under ``/settings/app-info``."""

    def __init__(self):
        super().__init__()
        self.update_checker = UpdateChecker()

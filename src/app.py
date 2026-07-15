import logging

import flet as ft

from UI.home_page import HomePage
from core.application.collection_manager import CollectionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


async def entrypoint(page: ft.Page):
    page.title = "Touched Grass Yet"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 500
    page.window.height = 600

    manager = CollectionManager()

    HomePage(page, manager)
    page.update()

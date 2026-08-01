import logging

import flet as ft

from utils.models import AppLayout
from utils.constants import DEFAULT_PAGE_HEIGHT, DEFAULT_PAGE_WIDTH

logger = logging.getLogger(__name__)


class BaseScreen(ft.Container):
    def __init__(
        self,
    ):
        super().__init__()

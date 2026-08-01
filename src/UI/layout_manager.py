import logging

from utils.constants import (
    MIN_PAGE_HEIGHT,
    MIN_PAGE_WIDTH,
    MOBILE_BREAKPOINT,
    TABLET_BREAKPOINT,
)
from utils.models import AppLayout, ScreenOrientation

logger = logging.getLogger(__name__)


def app_layout_resolver(page_width: float, page_height: float, **kwargs) -> AppLayout:
    """Return a responsive layout tuned to the available viewport.

    Args:
        page_width: Current page width reported by Flet.
        page_height: Current page height reported by Flet.

    Returns:
        A complete immutable layout snapshot for board, clock, captured pieces,
        settings, home, and developer controls.
    """

    width = max(float(page_width or 0), MIN_PAGE_WIDTH)
    height = max(float(page_height or 0), MIN_PAGE_HEIGHT)
    logger.debug("Resolving app layout: width=%s, height=%s", width, height)

    # Mobile gets a stacked layout because the board needs most of the width.
    if width < MOBILE_BREAKPOINT:
        screen_orientation = "mobile"
        padding = 12
    elif width < TABLET_BREAKPOINT:
        screen_orientation = "tablet"
        padding = 18
    else:
        screen_orientation = "desktop"
        padding = 24

    return AppLayout(
        screen_orientation=screen_orientation,
        width=width,
        height=height,
        padding=padding,
    )

import logging

from utils.models import AppLayout
from utils.constants import MIN_PAGE_WIDTH, MIN_PAGE_HEIGHT, MOBILE_BREAKPOINT, TABLET_BREAKPOINT


logger = logging.getLogger(__name__)

def resolve_app_layout(page_width: float, page_height: float) -> AppLayout:
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
        resolved_breakpoint = "mobile"
        padding = 12
        gap = 12
    elif width < TABLET_BREAKPOINT:
        resolved_breakpoint = "tablet"
        padding = 18
        gap = 16
    else:
        resolved_breakpoint = "desktop"
        padding = 24
        gap = 20

    return AppLayout(
        resolved_breakpoint=resolved_breakpoint,
        width=width,
        height=height,
        padding=padding,
        gap=gap,
    )
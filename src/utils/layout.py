import logging

from utils.constants import (
    COMPACT_BREAKPOINT,
    COMPACT_HEIGHT_BREAKPOINT,
    EXPANDED_BREAKPOINT,
    LARGE_BREAKPOINT,
    MEDIUM_BREAKPOINT,
    MEDIUM_HEIGHT_BREAKPOINT,
    MIN_PAGE_HEIGHT,
    MIN_PAGE_WIDTH,
)
from utils.models import (
    AppLayout,
    NavigationPattern,
    Orientation,
    ScreenFormFactor,
    WindowHeightClass,
    WindowWidthClass,
)

logger = logging.getLogger(__name__)


def _resolve_width_class(width: float) -> WindowWidthClass:
    if width < COMPACT_BREAKPOINT:
        return WindowWidthClass.COMPACT
    if width < MEDIUM_BREAKPOINT:
        return WindowWidthClass.MEDIUM
    if width < EXPANDED_BREAKPOINT:
        return WindowWidthClass.EXPANDED
    if width < LARGE_BREAKPOINT:
        return WindowWidthClass.LARGE
    return WindowWidthClass.EXTRA_LARGE


def _resolve_height_class(height: float) -> WindowHeightClass:
    if height < COMPACT_HEIGHT_BREAKPOINT:
        return WindowHeightClass.COMPACT
    if height < MEDIUM_HEIGHT_BREAKPOINT:
        return WindowHeightClass.MEDIUM
    return WindowHeightClass.EXPANDED


def _resolve_orientation(
    width: float, height: float, media_orientation: Orientation | None
) -> Orientation:
    if media_orientation is not None:
        return media_orientation
    return Orientation.LANDSCAPE if width >= height else Orientation.PORTRAIT


def _resolve_form_factor(
    width_class: WindowWidthClass,
    height_class: WindowHeightClass,
    orientation: Orientation,
) -> ScreenFormFactor:
    if width_class is WindowWidthClass.COMPACT:
        return ScreenFormFactor.MOBILE
    if width_class is WindowWidthClass.MEDIUM:
        # Phone landscape: medium width but compact height — stacked layout
        # stays (M3: two-pane layouts are not practical here).
        if height_class is WindowHeightClass.COMPACT:
            return ScreenFormFactor.MOBILE
        return ScreenFormFactor.TABLET_PORTRAIT
    if width_class is WindowWidthClass.EXPANDED:
        return ScreenFormFactor.TABLET_LANDSCAPE
    return ScreenFormFactor.DESKTOP


def _resolve_navigation(form_factor: ScreenFormFactor) -> NavigationPattern:
    match form_factor:
        case ScreenFormFactor.MOBILE:
            return NavigationPattern.BOTTOM_BAR
        case ScreenFormFactor.TABLET_PORTRAIT:
            return NavigationPattern.MINI_RAIL
        case ScreenFormFactor.TABLET_LANDSCAPE | ScreenFormFactor.DESKTOP:
            return NavigationPattern.EXTENDED_RAIL
        case _:
            return NavigationPattern.BOTTOM_BAR


def _resolve_padding(form_factor: ScreenFormFactor) -> float:
    match form_factor:
        case ScreenFormFactor.MOBILE:
            return 12
        case ScreenFormFactor.TABLET_PORTRAIT:
            return 16
        case ScreenFormFactor.TABLET_LANDSCAPE:
            return 20
        case ScreenFormFactor.DESKTOP:
            return 24
        case _:
            return 16


def _resolve_content_max_width(form_factor: ScreenFormFactor) -> float:
    match form_factor:
        case ScreenFormFactor.MOBILE | ScreenFormFactor.TABLET_PORTRAIT:
            return 0.0  # unconstrained: screens use the full width
        case ScreenFormFactor.TABLET_LANDSCAPE:
            return 1000
        case ScreenFormFactor.DESKTOP:
            return 1200
        case _:
            return 0.0


def _resolve_spacing(form_factor: ScreenFormFactor) -> float:
    match form_factor:
        case ScreenFormFactor.MOBILE:
            return 4
        case ScreenFormFactor.TABLET_PORTRAIT:
            return 4
        case ScreenFormFactor.TABLET_LANDSCAPE:
            return 8
        case ScreenFormFactor.DESKTOP:
            return 8
        case _:
            return 4


def app_layout_resolver(
    page_width: float,
    page_height: float,
    *,
    media=None,
    **kwargs,
) -> AppLayout:
    """Return a responsive layout tuned to the available viewport.

    Classifies the viewport into Material 3 window size classes (width and
    height separately), derives a :class:`ScreenFormFactor`, and resolves the
    design metrics (padding, spacing, content cap, navigation pattern) that
    the shell and navigation controls consume.

    Args:
        page_width: Current page width reported by Flet.
        page_height: Current page height reported by Flet.
        media: Optional ``page.media`` object exposing ``orientation`` and
            ``padding`` (left, top, right, bottom system insets). ``None`` is
            tolerated for headless runs and early page loads.

    Returns:
        A complete immutable layout snapshot for the current page size.
    """

    width_raw = float(page_width or 0)
    height_raw = float(page_height or 0)
    logger.debug("Resolving app layout: width=%s, height=%s", width_raw, height_raw)

    # Classify on the true window size (falling back to minimums only when the
    # viewport is still reporting 0); clamp only the stored values so a real
    # phone-landscape window (e.g. 700x400) is not reclassified.
    width_class = _resolve_width_class(width_raw or MIN_PAGE_WIDTH)
    height_class = _resolve_height_class(height_raw or MIN_PAGE_HEIGHT)
    width = max(width_raw, MIN_PAGE_WIDTH)
    height = max(height_raw, MIN_PAGE_HEIGHT)

    media_orientation = None
    if media is not None:
        media_orientation = getattr(media, "orientation", None)
    orientation = _resolve_orientation(width, height, media_orientation)

    form_factor = _resolve_form_factor(width_class, height_class, orientation)

    safe_padding = (0.0, 0.0, 0.0, 0.0)
    if media is not None:
        padding = getattr(media, "padding", None)
        if padding is not None:
            safe_padding = (
                getattr(padding, "left", 0.0) or 0.0,
                getattr(padding, "top", 0.0) or 0.0,
                getattr(padding, "right", 0.0) or 0.0,
                getattr(padding, "bottom", 0.0) or 0.0,
            )

    return AppLayout(
        screen_form_factor=form_factor,
        width=width,
        height=height,
        padding=_resolve_padding(form_factor),
        orientation=orientation,
        width_class=width_class,
        height_class=height_class,
        navigation=_resolve_navigation(form_factor),
        safe_padding=safe_padding,
        content_max_width=_resolve_content_max_width(form_factor),
        spacing=_resolve_spacing(form_factor),
    )

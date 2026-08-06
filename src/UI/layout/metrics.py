"""Layout-driven presentation metrics for the custom navigation controls.

Every numeric that the custom drawer and floating navigation bar need
(widths, paddings, margins, gaps) is derived from the resolved
:class:`AppLayout` instead of being hardcoded inside the controls. A window
resize therefore re-derives the whole navigation chrome automatically.

The resolver functions are pure: :class:`AppLayout` in, frozen metric
dataclass out. The controls call them from ``apply_layout()``.
"""

from __future__ import annotations

from dataclasses import dataclass

from utils.constants import (
    COMPACT_BREAKPOINT,
    EXTENDED_RAIL_MAX_WIDTH,
    EXTENDED_RAIL_MIN_WIDTH,
    MINI_RAIL_WIDTH,
)
from utils.models import AppLayout, NavigationPattern, WindowHeightClass


@dataclass(frozen=True)
class DrawerMetrics:
    """Numbers the custom drawer needs for the current layout."""

    width: float
    destination_padding: float
    item_spacing: float


@dataclass(frozen=True)
class NavBarMetrics:
    """Numbers the floating bottom navigation bar needs for the current layout."""

    margin_left: float
    margin_right: float
    margin_bottom: float
    destination_padding: float
    item_spacing: float


def resolve_drawer_metrics(layout: AppLayout) -> DrawerMetrics:
    """Derive drawer/rail metrics from *layout*.

    Mini rail (tablet portrait): fixed narrow width — icons only, labels
    hidden. Extended rail (tablet landscape and desktop): width scales with
    the viewport between :data:`EXTENDED_RAIL_MIN_WIDTH` and
    :data:`EXTENDED_RAIL_MAX_WIDTH`, with a roomier destination padding on
    wide layouts.
    """
    if layout.navigation is NavigationPattern.MINI_RAIL:
        return DrawerMetrics(
            width=float(MINI_RAIL_WIDTH),
            destination_padding=8.0,
            item_spacing=4.0,
        )

    width = min(
        max(layout.width * 0.22, EXTENDED_RAIL_MIN_WIDTH), EXTENDED_RAIL_MAX_WIDTH
    )
    wide = layout.padding >= 20  # tablet landscape / desktop spacing scale
    return DrawerMetrics(
        width=float(width),
        destination_padding=12.0 if wide else 8.0,
        item_spacing=8.0 if wide else 4.0,
    )


def resolve_navbar_metrics(layout: AppLayout) -> NavBarMetrics:
    """Derive floating bottom bar metrics from *layout*.

    The bottom margin always clears the system gesture area (safe inset),
    so the pill never collides with the Android navigation bar. Phone
    landscape (compact height) sits lower and wider.
    """
    _, _, _, safe_bottom = layout.safe_padding
    compact_height = layout.height_class is WindowHeightClass.COMPACT
    wide = layout.width >= COMPACT_BREAKPOINT

    margin_h = 24.0 if wide else 16.0
    margin_bottom = (16.0 if compact_height else 24.0) + safe_bottom
    destination_padding = 10.0 if wide else 8.0

    return NavBarMetrics(
        margin_left=margin_h,
        margin_right=margin_h,
        margin_bottom=margin_bottom,
        destination_padding=destination_padding,
        item_spacing=4.0,
    )

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class OSType(Enum):
    UNKNOWN = 0
    WINDOWS = 1
    ANDROID = 2


class ScreenFormFactor(Enum):
    UNKNOWN = 0
    MOBILE = 1
    TABLET_PORTRAIT = 2
    TABLET_LANDSCAPE = 3
    DESKTOP = 4


class WindowWidthClass(Enum):
    """Material 3 width window size classes."""

    COMPACT = 0  # < 600dp  — phones portrait
    MEDIUM = 1  # 600-839dp — tablets portrait, foldables
    EXPANDED = 2  # 840-1199dp — tablets landscape
    LARGE = 3  # 1200-1599dp — large tablets / small desktops
    EXTRA_LARGE = 4  # >= 1600dp — desktops


class WindowHeightClass(Enum):
    """Material 3 height window size classes."""

    COMPACT = 0  # < 480dp — phones landscape
    MEDIUM = 1  # 480-899dp — phones portrait, tablets landscape
    EXPANDED = 2  # >= 900dp — tablets portrait


class NavigationPattern(Enum):
    """Which navigation chrome fits the current window size."""

    BOTTOM_BAR = 0
    MINI_RAIL = 1
    EXTENDED_RAIL = 2


class Orientation(Enum):
    PORTRAIT = 0
    LANDSCAPE = 1


@dataclass
class Tick:
    watcher: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WatcherConfig:
    name: str = ""
    interval_s: float = 1.0
    enabled: bool = True


@dataclass
class RawEvent:
    id: int = 0
    device_id: str = ""
    platform: str = ""
    event_type: str = ""
    timestamp: float = 0.0
    collected_at: float = 0.0
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass(frozen=True)
class AppLayout:
    """Resolved responsive metrics for the current page size.

    The dataclass is frozen because it represents one layout calculation. When
    the page changes size, callers ask :func:`app_layout_resolver` for a new
    instance and pass it to each control.

    ``safe_padding`` mirrors the system insets (notch, status bar, gesture
    navigation bar, keyboard) reported by ``page.media``; design spacing lives
    in ``padding`` and ``spacing``. Both are consumed by the shell and the
    custom navigation controls to derive their margins automatically.
    """

    screen_form_factor: ScreenFormFactor
    width: float
    height: float
    padding: float = 16.0
    orientation: Orientation = Orientation.LANDSCAPE
    width_class: WindowWidthClass = WindowWidthClass.EXTRA_LARGE
    height_class: WindowHeightClass = WindowHeightClass.MEDIUM
    navigation: NavigationPattern = NavigationPattern.EXTENDED_RAIL
    safe_padding: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    content_max_width: float = 0.0
    spacing: float = 4.0

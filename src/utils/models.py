from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Union


class OSType(Enum):
    UNKNOWN = 0
    WINDOWS = 1
    ANDROID = 2


class ScreenOrientation(Enum):
    UNKNOWN = 0
    LANDSCAPE_ONLY = 1
    PORTAIT_ONLY = 2
    AUTO = 3

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
    the page changes size, callers ask :func:`resolve_app_layout` for a new
    instance and pass it to each control.
    """

    screen_orientation: ScreenOrientation | str
    width: float
    height: float
    padding: float

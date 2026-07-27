from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class Destination(Enum):
    DASHBOARD = auto()
    TIMELINE = auto()
    ANALYTICS = auto()
    SETTINGS = auto()


class CollectionStatus(Enum):
    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()


class ThemeMode(Enum):
    SYSTEM = auto()
    LIGHT = auto()
    DARK = auto()


@dataclass
class AppSummary:
    app_key: str
    total_seconds: float
    session_count: int
    color: str = ""


class AppState:
    def __init__(self) -> None:
        self._observers: dict[str, list[Callable[[], None]]] = {}

        self._current_destination = Destination.DASHBOARD
        self._sidebar_open = True
        self._context_open = False
        self._context_content: Any = None

        self._collection_status = CollectionStatus.STOPPED
        self._today_seconds: float = 0.0
        self._collection_interval_s: float = 5.0
        self._battery_pct: int | None = None
        self._battery_charging: bool | None = None

        self._theme_mode = ThemeMode.SYSTEM
        self._seed_color_name: str = "purple"
        self._foreground_enabled = True
        self._afk_enabled = True
        self._power_enabled = True
        self._url_extraction_enabled = False
        self._focus_productive_categories: list[str] = field(default_factory=lambda: [])

        self._top_apps: list[AppSummary] = []
        self._today_sessions: Sequence[dict[str, Any]] = []
        self._weekly_data: dict[str, float] = {}

    def subscribe(self, key: str, callback: Callable[[], None]) -> Callable[[], None]:
        if key not in self._observers:
            self._observers[key] = []
        self._observers[key].append(callback)
        return lambda: self._observers[key].remove(callback)

    def _notify(self, key: str) -> None:
        for cb in self._observers.get(key, []):
            cb()

    @property
    def current_destination(self) -> Destination:
        return self._current_destination

    @current_destination.setter
    def current_destination(self, value: Destination) -> None:
        if self._current_destination != value:
            self._current_destination = value
            self._notify("current_destination")

    @property
    def sidebar_open(self) -> bool:
        return self._sidebar_open

    @sidebar_open.setter
    def sidebar_open(self, value: bool) -> None:
        if self._sidebar_open != value:
            self._sidebar_open = value
            self._notify("sidebar_open")

    @property
    def context_open(self) -> bool:
        return self._context_open

    @context_open.setter
    def context_open(self, value: bool) -> None:
        if self._context_open != value:
            self._context_open = value
            self._notify("context_open")

    @property
    def context_content(self) -> Any:
        return self._context_content

    @context_content.setter
    def context_content(self, value: Any) -> None:
        self._context_content = value
        self._notify("context_content")

    @property
    def collection_status(self) -> CollectionStatus:
        return self._collection_status

    @collection_status.setter
    def collection_status(self, value: CollectionStatus) -> None:
        if self._collection_status != value:
            self._collection_status = value
            self._notify("collection_status")

    @property
    def today_seconds(self) -> float:
        return self._today_seconds

    @today_seconds.setter
    def today_seconds(self, value: float) -> None:
        if self._today_seconds != value:
            self._today_seconds = value
            self._notify("today_seconds")

    @property
    def collection_interval_s(self) -> float:
        return self._collection_interval_s

    @collection_interval_s.setter
    def collection_interval_s(self, value: float) -> None:
        if self._collection_interval_s != value:
            self._collection_interval_s = value
            self._notify("settings")

    @property
    def battery_pct(self) -> int | None:
        return self._battery_pct

    @battery_pct.setter
    def battery_pct(self, value: int | None) -> None:
        if self._battery_pct != value:
            self._battery_pct = value
            self._notify("battery")

    @property
    def battery_charging(self) -> bool | None:
        return self._battery_charging

    @battery_charging.setter
    def battery_charging(self, value: bool | None) -> None:
        if self._battery_charging != value:
            self._battery_charging = value
            self._notify("battery")

    @property
    def theme_mode(self) -> ThemeMode:
        return self._theme_mode

    @theme_mode.setter
    def theme_mode(self, value: ThemeMode) -> None:
        if self._theme_mode != value:
            self._theme_mode = value
            self._notify("theme_mode")

    @property
    def seed_color_name(self) -> str:
        return self._seed_color_name

    @seed_color_name.setter
    def seed_color_name(self, value: str) -> None:
        if self._seed_color_name != value:
            self._seed_color_name = value
            self._notify("seed_color")

    @property
    def foreground_enabled(self) -> bool:
        return self._foreground_enabled

    @foreground_enabled.setter
    def foreground_enabled(self, value: bool) -> None:
        if self._foreground_enabled != value:
            self._foreground_enabled = value
            self._notify("settings")

    @property
    def afk_enabled(self) -> bool:
        return self._afk_enabled

    @afk_enabled.setter
    def afk_enabled(self, value: bool) -> None:
        if self._afk_enabled != value:
            self._afk_enabled = value
            self._notify("settings")

    @property
    def power_enabled(self) -> bool:
        return self._power_enabled

    @power_enabled.setter
    def power_enabled(self, value: bool) -> None:
        if self._power_enabled != value:
            self._power_enabled = value
            self._notify("settings")

    @property
    def url_extraction_enabled(self) -> bool:
        return self._url_extraction_enabled

    @url_extraction_enabled.setter
    def url_extraction_enabled(self, value: bool) -> None:
        if self._url_extraction_enabled != value:
            self._url_extraction_enabled = value
            self._notify("settings")

    @property
    def top_apps(self) -> list[AppSummary]:
        return self._top_apps

    @top_apps.setter
    def top_apps(self, value: list[AppSummary]) -> None:
        self._top_apps = value
        self._notify("top_apps")

    @property
    def focus_productive_categories(self) -> list[str]:
        return self._focus_productive_categories

    @focus_productive_categories.setter
    def focus_productive_categories(self, value: list[str]) -> None:
        self._focus_productive_categories = value
        self._notify("focus_settings")






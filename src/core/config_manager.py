import json
import logging
import os
from copy import deepcopy
from pathlib import Path

from utils.paths import get_data_dir

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "collection_enabled": True,
    "url_extraction_enabled": True,
    "tick_interval_overrides": {},
    "watchers_enabled": ["foreground", "afk"],
    "log_level": "INFO",
    "auto_start_enabled": False,
    "theme_mode": "system",
    "auto_update_enabled": True,
    "start_maximized": True,
    "afk_idle_threshold_s": 60.0,
    "afk_away_threshold_s": 300.0,
}


class ConfigManager:
    def __init__(self, path: str | Path | None = None):
        self._path = Path(path or os.path.join(get_data_dir(), "config.json"))
        self._data: dict = deepcopy(DEFAULT_CONFIG)

    def load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    loaded = json.load(f)
                self._data = {**deepcopy(DEFAULT_CONFIG), **loaded}
                logger.info("Config loaded from %s", self._path)
            except Exception:
                logger.exception("Failed to load config, using defaults")
                self._data = deepcopy(DEFAULT_CONFIG)
        else:
            logger.info("No config file at %s, using defaults", self._path)
            self._data = deepcopy(DEFAULT_CONFIG)

    def save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            logger.info("Config saved to %s", self._path)
        except Exception:
            logger.exception("Failed to save config")

    @property
    def collection_enabled(self) -> bool:
        return self._data.get("collection_enabled", True)

    @collection_enabled.setter
    def collection_enabled(self, value: bool) -> None:
        self._data["collection_enabled"] = value

    def get_interval(self, watcher_name: str, default: float) -> float:
        overrides = self._data.get("tick_interval_overrides", {})
        return overrides.get(watcher_name, default)

    def set_interval(self, watcher_name: str, seconds: float) -> None:
        overrides = self._data.setdefault("tick_interval_overrides", {})
        if seconds > 0:
            overrides[watcher_name] = seconds
        else:
            overrides.pop(watcher_name, None)

    @property
    def watchers_enabled(self) -> list[str]:
        return self._data.get("watchers_enabled", ["foreground", "afk"])

    @watchers_enabled.setter
    def watchers_enabled(self, value: list[str]) -> None:
        self._data["watchers_enabled"] = list(value)

    @property
    def url_extraction_enabled(self) -> bool:
        return self._data.get("url_extraction_enabled", True)

    @url_extraction_enabled.setter
    def url_extraction_enabled(self, value: bool) -> None:
        self._data["url_extraction_enabled"] = value

    @property
    def auto_start_enabled(self) -> bool:
        return self._data.get("auto_start_enabled", False)

    @auto_start_enabled.setter
    def auto_start_enabled(self, value: bool) -> None:
        self._data["auto_start_enabled"] = value

    @property
    def log_level(self) -> str:
        return self._data.get("log_level", "INFO")

    @log_level.setter
    def log_level(self, value: str) -> None:
        self._data["log_level"] = value.upper()

    @property
    def theme_mode(self) -> str:
        return self._data.get("theme_mode", "system")

    @theme_mode.setter
    def theme_mode(self, value: str) -> None:
        self._data["theme_mode"] = value

    @property
    def auto_update_enabled(self) -> bool:
        return self._data.get("auto_update_enabled", True)

    @auto_update_enabled.setter
    def auto_update_enabled(self, value: bool) -> None:
        self._data["auto_update_enabled"] = value

    @property
    def start_maximized(self) -> bool:
        return self._data.get("start_maximized", True)

    @start_maximized.setter
    def start_maximized(self, value: bool) -> None:
        self._data["start_maximized"] = value

    @property
    def afk_idle_threshold_s(self) -> float:
        return float(self._data.get("afk_idle_threshold_s", 60.0))

    @afk_idle_threshold_s.setter
    def afk_idle_threshold_s(self, value: float) -> None:
        self._data["afk_idle_threshold_s"] = max(0.0, float(value))

    @property
    def afk_away_threshold_s(self) -> float:
        return float(self._data.get("afk_away_threshold_s", 300.0))

    @afk_away_threshold_s.setter
    def afk_away_threshold_s(self, value: float) -> None:
        self._data["afk_away_threshold_s"] = max(0.0, float(value))

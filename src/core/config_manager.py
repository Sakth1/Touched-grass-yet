import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "collection_enabled": True,
    "tick_interval_overrides": {},
    "watchers_enabled": ["foreground", "afk"],
    "log_level": "INFO",
}


class ConfigManager:
    def __init__(self, path: str | None = None):
        self._path = Path(path or "config.json")
        self._data: dict = dict(DEFAULT_CONFIG)

    def load(self) -> None:
        if self._path.exists():
            try:
                with open(self._path) as f:
                    loaded = json.load(f)
                self._data = {**DEFAULT_CONFIG, **loaded}
                logger.info("Config loaded from %s", self._path)
            except Exception:
                logger.exception("Failed to load config, using defaults")
                self._data = dict(DEFAULT_CONFIG)
        else:
            logger.info("No config file at %s, using defaults", self._path)
            self._data = dict(DEFAULT_CONFIG)

    def save(self) -> None:
        try:
            with open(self._path, "w") as f:
                json.dump(self._data, f, indent=2)
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

    @property
    def watchers_enabled(self) -> list[str]:
        return self._data.get("watchers_enabled", ["foreground", "afk"])

    @property
    def log_level(self) -> str:
        return self._data.get("log_level", "INFO")

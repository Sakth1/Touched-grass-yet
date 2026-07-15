import logging

from core.config_manager import ConfigManager
from core.collectors.base import Watcher
from core.collectors.windows.foreground import ForegroundWatcher
from core.collectors.windows.afk import AfkWatcher
from core.collectors.windows.power import PowerWatcher

logger = logging.getLogger(__name__)


class WindowsRuntime:
    def __init__(self, config: ConfigManager):
        self._config = config

    def create_watchers(self) -> list[Watcher]:
        enabled = self._config.watchers_enabled
        all_watchers = {
            "foreground": ForegroundWatcher,
            "afk": AfkWatcher,
            "power": PowerWatcher,
        }
        watchers: list[Watcher] = []
        for name, cls in all_watchers.items():
            if name in enabled:
                watchers.append(cls())
        logger.info("Created %d Windows watchers: %s", len(watchers), enabled)
        return watchers

    def shutdown(self) -> None:
        logger.info("Windows runtime shutdown")

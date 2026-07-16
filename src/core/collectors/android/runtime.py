import logging

from utils.models import WatcherConfig
from core.config_manager import ConfigManager
from core.collectors.base import Watcher
from core.collectors.android.foreground import AndroidForegroundWatcher

logger = logging.getLogger(__name__)

_DEFAULT_POLL_INTERVAL = 60.0


class AndroidRuntime:
    def __init__(self, config: ConfigManager):
        self._config = config

    def create_watchers(self) -> list[Watcher]:
        enabled = self._config.watchers_enabled
        all_watchers = {
            "android_foreground": AndroidForegroundWatcher,
        }

        if not any(name in enabled for name in all_watchers):
            enabled = list(all_watchers.keys())
            logger.info("No Android watchers in config, using defaults: %s", enabled)

        watchers: list[Watcher] = []
        for name, cls in all_watchers.items():
            if name in enabled:
                interval = self._config.get_interval(name, _DEFAULT_POLL_INTERVAL)
                wc = WatcherConfig(name=name, interval_s=interval, enabled=True)
                watchers.append(cls(wc))
        logger.info("Created %d Android watchers", len(watchers))
        return watchers

    def shutdown(self) -> None:
        logger.info("Android runtime shutdown")

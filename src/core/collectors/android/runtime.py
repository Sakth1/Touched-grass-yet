import logging

from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class AndroidRuntime:
    def __init__(self, config: ConfigManager):
        self._config = config

    def create_watchers(self) -> list:
        logger.info("Android runtime created (no watchers yet)")
        return []

    def shutdown(self) -> None:
        logger.info("Android runtime shutdown")

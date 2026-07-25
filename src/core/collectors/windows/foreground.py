import logging

from core.collectors.windows.browser import analyze as analyze_browser
from core.collectors.windows.window import WindowAnalyzer
from core.config_manager import ConfigManager
from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)


class ForegroundWatcher:
    def __init__(self, config: WatcherConfig | None = None, app_config: ConfigManager | None = None):
        self.config = config or WatcherConfig(
            name="foreground",
            interval_s=2.0,
            enabled=True,
        )
        self._url_extractor = None
        if app_config and app_config.url_extraction_enabled:
            try:
                from core.collectors.windows.url_extractor import UrlExtractor
                self._url_extractor = UrlExtractor()
                logger.info("URL extraction enabled")
            except Exception:
                logger.exception("Failed to initialize URL extractor")

    async def tick(self) -> Tick | None:
        window_data = WindowAnalyzer.analyze()
        if window_data is None:
            return None

        browser_info = analyze_browser(window_data["app"], window_data["title"])
        if browser_info is not None:
            window_data["browser"] = browser_info.browser
            if self._url_extractor:
                url = self._url_extractor.extract(
                    browser_info.browser,
                    window_title=window_data.get("title"),
                    window_pid=window_data.get("pid"),
                )
                if url:
                    window_data["url"] = url
            else:
                window_data["page_title"] = browser_info.page_title
                if browser_info.inferred_domain:
                    window_data["inferred_domain"] = browser_info.inferred_domain

        return Tick(
            watcher="foreground",
            data=window_data,
        )

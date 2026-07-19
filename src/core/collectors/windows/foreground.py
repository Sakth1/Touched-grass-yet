import logging

from core.collectors.windows.browser import analyze as analyze_browser
from core.collectors.windows.window import WindowAnalyzer
from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)


class ForegroundWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="foreground",
            interval_s=2.0,
            enabled=True,
        )

    async def tick(self) -> Tick | None:
        window_data = WindowAnalyzer.analyze()
        if window_data is None:
            return None

        browser_info = analyze_browser(window_data["app"], window_data["title"])
        if browser_info is not None:
            window_data["browser"] = browser_info.browser
            window_data["page_title"] = browser_info.page_title
            if browser_info.inferred_domain:
                window_data["inferred_domain"] = browser_info.inferred_domain

        return Tick(
            watcher="foreground",
            data=window_data,
        )

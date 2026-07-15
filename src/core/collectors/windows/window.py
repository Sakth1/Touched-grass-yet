import logging

import psutil
import win32gui
import win32process

from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)


class WindowWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="window",
            interval_s=2.0,
            enabled=True,
        )

    async def tick(self) -> Tick | None:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            try:
                proc = psutil.Process(pid)
                app = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = "unknown"

            return Tick(
                watcher="window",
                data={
                    "app": app,
                    "title": title,
                },
            )
        except Exception:
            logger.exception("Window tick failed")
            return None

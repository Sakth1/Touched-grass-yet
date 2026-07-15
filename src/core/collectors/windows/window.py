import logging

import psutil
import win32gui
import win32process

logger = logging.getLogger(__name__)


class WindowAnalyzer:
    @staticmethod
    def analyze() -> dict | None:
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

            return {"app": app, "title": title}
        except Exception:
            logger.exception("Window analysis failed")
            return None

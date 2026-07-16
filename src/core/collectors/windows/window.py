import ctypes
import ctypes.wintypes
import logging

import psutil

logger = logging.getLogger(__name__)

_user32 = ctypes.windll.user32
_user32.GetForegroundWindow.restype = ctypes.wintypes.HWND
_user32.GetWindowTextW.restype = ctypes.c_int
_user32.GetWindowTextW.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPWSTR,
    ctypes.c_int,
]
_user32.GetWindowThreadProcessId.restype = ctypes.wintypes.DWORD
_user32.GetWindowThreadProcessId.argtypes = [
    ctypes.wintypes.HWND,
    ctypes.POINTER(ctypes.wintypes.DWORD),
]


class WindowAnalyzer:
    @staticmethod
    def analyze() -> dict | None:
        try:
            hwnd = _user32.GetForegroundWindow()
            if not hwnd:
                return None

            buf = ctypes.create_unicode_buffer(512)
            _user32.GetWindowTextW(hwnd, buf, 512)
            title = buf.value

            pid = ctypes.wintypes.DWORD()
            _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            try:
                proc = psutil.Process(pid.value)
                app = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                app = "unknown"

            return {"app": app, "title": title}
        except Exception:
            logger.exception("Window analysis failed")
            return None

import ctypes

from utils.models import Tick, WatcherConfig


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


_kernel32 = ctypes.windll.kernel32
_user32 = ctypes.windll.user32
_kernel32.GetTickCount64.restype = ctypes.c_ulonglong


def _idle_seconds() -> float:
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if not _user32.GetLastInputInfo(ctypes.byref(lii)):
        return 0.0
    tick64 = _kernel32.GetTickCount64()
    tick_lower32 = tick64 & 0xFFFFFFFF
    if tick_lower32 >= lii.dwTime:
        diff_ms = tick_lower32 - lii.dwTime
    else:
        diff_ms = (0x100000000 - lii.dwTime) + tick_lower32
    return diff_ms / 1000.0


class AfkWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="afk",
            interval_s=5.0,
            enabled=True,
        )

    async def tick(self) -> Tick | None:
        idle = _idle_seconds()
        status = "active"
        if idle > 300:
            status = "away"
        elif idle > 60:
            status = "idle"
        return Tick(
            watcher="afk",
            data={
                "status": status,
                "idle_seconds": idle,
            },
        )

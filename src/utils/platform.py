import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from utils.models import OSType

if TYPE_CHECKING:
    import winreg
else:
    try:
        import winreg
    except ImportError:
        winreg = None


def get_winreg():
    """Return the ``winreg`` module or ``None`` on non-Windows platforms."""
    return winreg


def detect_os() -> OSType:
    system = platform.system()
    match system:
        case "Windows":
            return OSType.WINDOWS
        case "Android" | "Linux":
            return OSType.ANDROID
        case _:
            return OSType.UNKNOWN


def is_packaged() -> bool:
    """True when running from a bundled executable (not from source)."""
    if getattr(sys, "frozen", False):
        return True
    exe = Path(sys.executable).name.lower()
    return exe.endswith(".exe") and not exe.startswith(("python", "flet"))

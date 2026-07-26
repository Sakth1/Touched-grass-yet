import logging
import sys
from pathlib import Path

try:
    import winreg
except ImportError:
    winreg = None

logger = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "TouchedGrassYet"


def _get_target_path() -> str | None:
    if winreg is None:
        return None
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).resolve())
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    script = Path(__file__).resolve().parent.parent / "main.py"
    if not script.exists():
        logger.warning("main.py not found for dev-mode auto-start")
        return None
    return f'"{pythonw}" "{script}"'


def enable() -> bool:
    target = _get_target_path()
    if target is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, target)
        winreg.CloseKey(key)
        logger.info("Auto-start enabled: %s", target)
        return True
    except Exception:
        logger.exception("Failed to enable auto-start")
        return False


def disable() -> bool:
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, VALUE_NAME)
        winreg.CloseKey(key)
        logger.info("Auto-start disabled")
        return True
    except FileNotFoundError:
        return True
    except Exception:
        logger.exception("Failed to disable auto-start")
        return False


def is_enabled() -> bool:
    if winreg is None:
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_QUERY_VALUE)
        winreg.QueryValueEx(key, VALUE_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        logger.exception("Failed to query auto-start")
        return False

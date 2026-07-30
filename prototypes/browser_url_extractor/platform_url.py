"""Platform-specific URL extraction via accessibility APIs.

Windows (tested):  UIA via pywinauto (primary) + uiautomation (fallback)
macOS (stub):      AppleScript / osascript (untested)
Linux (stub):      AT-SPI2 / PyGObject (untested), xdotool fallback (untested)
"""

import ctypes
import platform
import subprocess
from ctypes import wintypes

from browser_url_extractor.utils import is_trackable_url, normalize_url

SYSTEM = platform.system()


def _get_foreground_window_pid() -> tuple[int, str] | None:
    try:
        user32 = ctypes.windll.user32
        handle = user32.GetForegroundWindow()
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(handle, ctypes.byref(pid))
        length = user32.GetWindowTextLengthW(handle) + 1
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(handle, buf, length)
        title = buf.value or ""
        return pid.value, title
    except Exception:
        return None


def _find_url_via_pywinauto() -> str | None:
    try:
        from pywinauto import Application
    except ImportError:
        return None

    fg = _get_foreground_window_pid()
    if fg is None:
        return None
    fg_pid, fg_title = fg

    browser_names = {
        "google chrome": "Address and search bar",
        "brave": "Address and search bar",
        "microsoft edge": "Address and search bar",
        "mozilla firefox": "Search or enter address",
        "opera": "Address field",
        "vivaldi": "Search or enter an address",
    }

    match = None
    title_lower = fg_title.lower()
    for brand, addr_name in browser_names.items():
        if brand.split()[0] in title_lower:
            match = (brand, addr_name)
            break
    if match is None:
        return None

    try:
        app = Application(backend="uia").connect(process=fg_pid)
        dlg = app.top_window()
        for e in dlg.descendants(control_type="Edit"):
            try:
                name = e.element_info.name
                if name == match[1]:
                    url = e.get_value()
                    url = normalize_url(url) if url else None
                    if url and is_trackable_url(url):
                        return url
            except Exception:
                continue
    except Exception:
        return None

    return None


def _find_url_via_uiautomation() -> str | None:
    try:
        import uiautomation as auto  # type: ignore
    except ImportError:
        return None

    addr_names = [
        "Address and search bar",
        "Search or enter address",
        "Address field",
        "Search or enter an address",
    ]

    def _check_edit(edit) -> str | None:
        try:
            val = edit.GetValuePattern().Value
            if val:
                val = normalize_url(val)
                if is_trackable_url(val):
                    return val
        except Exception:
            pass
        return None

    try:
        fg = auto.WindowControl(searchDepth=1, ClassName="Chrome_WidgetWin_1")
        fg.SetFocus()
        for e in fg.GetChildren():
            for child in e.GetChildren():
                if child.ControlType == auto.ControlType.Edit:
                    name = child.Name
                    if name in addr_names:
                        val = _check_edit(child)
                        if val:
                            return val
    except Exception:
        pass

    try:
        fg_wins = auto.GetRootControl().GetChildren()
        for w in fg_wins:
            if w.ClassName == "Chrome_WidgetWin_1":
                for e in w.GetChildren():
                    for child in e.GetChildren():
                        if child.ControlType == auto.ControlType.Edit:
                            val = _check_edit(child)
                            if val:
                                return val
    except Exception:
        pass

    return None


def _find_edit_by_name_windows(addr_names: list[str]) -> str | None:
    try:
        from pywinauto import Application, Desktop
    except ImportError:
        return None

    browser_classes = {
        "Chrome_WidgetWin_1": [
            "Google Chrome",
            "Brave",
            "Microsoft Edge",
            "Opera",
            "Vivaldi",
        ],
        "MozillaWindowClass": ["Mozilla Firefox"],
    }

    try:
        desktop = Desktop(backend="uia")
        for class_name, brands in browser_classes.items():
            try:
                windows = desktop.windows(class_name=class_name)
                for w in windows:
                    if not w.is_visible():
                        continue
                    wt = w.window_text().lower()
                    matched = any(b.lower().split()[0] in wt for b in brands)
                    if not matched:
                        continue
                    try:
                        app = Application(backend="uia").connect(handle=w.handle)
                        dlg = app.top_window()
                        for e in dlg.descendants(control_type="Edit"):
                            try:
                                if e.element_info.name in addr_names:
                                    url = e.get_value()
                                    url = normalize_url(url) if url else None
                                    if url and is_trackable_url(url):
                                        return url
                            except Exception:
                                continue
                    except Exception:
                        continue
            except Exception:
                continue
    except Exception:
        pass
    return None


def get_url_windows_uia() -> str | None:
    addr_names = [
        "Address and search bar",
        "Search or enter address",
        "Address field",
        "Search or enter an address",
    ]

    result = _find_url_via_pywinauto()
    if result:
        return result

    result = _find_edit_by_name_windows(addr_names)
    if result:
        return result

    result = _find_url_via_uiautomation()
    if result:
        return result

    return None


def get_url_macos_applescript() -> str | None:
    browsers = [
        "Google Chrome",
        "Safari",
        "Microsoft Edge",
        "Brave Browser",
        "Opera",
        "Vivaldi",
        "Firefox",
    ]

    for browser in browsers:
        script = f'tell application "{browser}"\n  return URL of active tab of front window\nend tell'
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                url = result.stdout.strip()
                url = normalize_url(url) if url else None
                if url and is_trackable_url(url):
                    return url
        except Exception:
            continue

    return None


def get_url_linux_atspi() -> str | None:
    try:
        import gi  # type: ignore

        gi.require_version("Atspi", "2.0")
        from gi.repository import Atspi  # type: ignore
    except ImportError:
        pass
    else:
        try:
            desktop = Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                name = app.get_name()
                if not name:
                    continue
                name_lower = name.lower()
                is_browser = any(
                    b in name_lower
                    for b in ["firefox", "chrome", "chromium", "brave", "edge"]
                )
                if not is_browser:
                    continue
                for j in range(app.get_child_count()):
                    win = app.get_child_at_index(j)
                    for k in range(win.get_child_count()):
                        child = win.get_child_at_index(k)
                        role = child.get_role()
                        if role in (Atspi.Role.ENTRY, Atspi.Role.COMBO_BOX):
                            try:
                                text = child.query_text()
                                url = text.get_text(0, -1)
                                url = normalize_url(url) if url else None
                                if url and is_trackable_url(url):
                                    return url
                            except Exception:
                                continue
        except Exception:
            pass

            try:
                result = subprocess.run(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    title = result.stdout.strip()
                    if title and is_trackable_url(title):
                        return title
            except Exception:
                pass

    return None


def get_active_url_platform() -> str | None:
    if SYSTEM == "Windows":
        return get_url_windows_uia()
    elif SYSTEM == "Darwin":
        return get_url_macos_applescript()
    elif SYSTEM == "Linux":
        return get_url_linux_atspi()
    return None

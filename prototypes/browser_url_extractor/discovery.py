import glob
import os
import platform

BROWSER_INFO: dict[str, dict] = {
    "chrome": {
        "windows": os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"
        ),
        "darwin": os.path.expanduser("~/Library/Application Support/Google/Chrome"),
        "linux": os.path.expanduser("~/.config/google-chrome"),
    },
    "brave": {
        "windows": os.path.join(
            os.environ.get("LOCALAPPDATA", ""),
            "BraveSoftware",
            "Brave-Browser",
            "User Data",
        ),
        "darwin": os.path.expanduser(
            "~/Library/Application Support/BraveSoftware/Brave-Browser"
        ),
        "linux": os.path.expanduser("~/.config/BraveSoftware/Brave-Browser"),
    },
    "edge": {
        "windows": os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data"
        ),
        "darwin": os.path.expanduser("~/Library/Application Support/Microsoft Edge"),
        "linux": os.path.expanduser("~/.config/microsoft-edge"),
    },
    "opera": {
        "windows": os.path.join(
            os.environ.get("APPDATA", ""), "Opera Software", "Opera Stable"
        ),
        "darwin": os.path.expanduser(
            "~/Library/Application Support/com.operasoftware.Opera"
        ),
        "linux": os.path.expanduser("~/.config/opera"),
    },
    "vivaldi": {
        "windows": os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "Vivaldi", "User Data"
        ),
        "darwin": os.path.expanduser("~/Library/Application Support/Vivaldi"),
        "linux": os.path.expanduser("~/.config/vivaldi"),
    },
}

FIREFOX_PATHS: dict[str, str] = {
    "windows": os.path.join(
        os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles"
    ),
    "darwin": os.path.expanduser("~/Library/Application Support/Firefox/Profiles"),
    "linux": os.path.expanduser("~/.mozilla/firefox"),
}

SYSTEM = platform.system()
IS_WINDOWS = SYSTEM == "Windows"
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"


def _platform_key() -> str:
    if IS_WINDOWS:
        return "windows"
    if IS_MACOS:
        return "darwin"
    return "linux"


def find_chromium_session_dirs(
    browser_name: str | None = None,
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    pk = _platform_key()

    for name, paths in BROWSER_INFO.items():
        if browser_name and name != browser_name:
            continue
        base = paths.get(pk, "")
        if not base or not os.path.isdir(base):
            continue

        local_state = os.path.join(base, "Local State")
        profiles = ["Default"]
        if os.path.isfile(local_state):
            try:
                import json

                with open(local_state, encoding="utf-8") as f:
                    data = json.load(f)
                info = data.get("profile", {}).get("info_cache", {})
                for prof in info:
                    profiles.append(prof)
            except Exception:
                pass

        for prof in set(profiles):
            sess_dir = os.path.join(base, prof, "Sessions")
            if os.path.isdir(sess_dir):
                results.append((name, sess_dir))
    return results


def find_firefox_session_dirs() -> list[tuple[str, str]]:
    pk = _platform_key()
    base = FIREFOX_PATHS.get(pk, "")
    if not base or not os.path.isdir(base):
        return []

    results = []
    for prof_dir in glob.glob(os.path.join(base, "*")):
        backups = os.path.join(prof_dir, "sessionstore-backups")
        if os.path.isdir(backups):
            results.append(("firefox", backups))
    return results


def find_all_session_dirs() -> list[tuple[str, str]]:
    return find_chromium_session_dirs() + find_firefox_session_dirs()

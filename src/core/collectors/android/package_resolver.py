import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)

_FALLBACK_NAMES = {
    "com.android.chrome": "Chrome",
    "com.android.browser": "Browser",
    "com.android.vending": "Google Play",
    "com.google.android.apps.maps": "Maps",
    "com.google.android.youtube": "YouTube",
    "com.google.android.gm": "Gmail",
    "com.google.android.googlequicksearchbox": "Google",
    "com.google.android.apps.docs": "Docs",
    "com.google.android.apps.photos": "Photos",
    "com.google.android.apps.messaging": "Messages",
    "com.google.android.calendar": "Calendar",
    "com.google.android.deskclock": "Clock",
    "com.google.android.contacts": "Contacts",
    "com.google.android.dialer": "Phone",
    "com.google.android.apps.tachyon": "Duo",
    "com.google.android.keep": "Keep",
    "com.google.android.apps.cloudprint": "Cloud Print",
    "org.telegram.messenger": "Telegram",
    "com.whatsapp": "WhatsApp",
    "com.facebook.katana": "Facebook",
    "com.facebook.orca": "Messenger",
    "com.instagram.android": "Instagram",
    "com.twitter.android": "X",
    "com.reddit.frontpage": "Reddit",
    "com.slack": "Slack",
    "com.microsoft.teams": "Teams",
    "com.microsoft.office.outlook": "Outlook",
    "com.microsoft.office.word": "Word",
    "com.microsoft.office.excel": "Excel",
    "com.microsoft.office.powerpoint": "PowerPoint",
    "com.spotify.music": "Spotify",
    "com.netflix.mediaclient": "Netflix",
    "com.zhiliaoapp.musically": "TikTok",
    "com.snapchat.android": "Snapchat",
    "com.ubercab": "Uber",
    "com.discord": "Discord",
    "com.github.android": "GitHub",
    "com.termux": "Termux",
    "com.duolingo": "Duolingo",
}

_PackageManager = None
_activity = None


def _get_activity():
    global _activity
    if _activity is not None:
        return _activity
    activity_host_class = os.getenv("MAIN_ACTIVITY_HOST_CLASS_NAME")
    if not activity_host_class:
        logger.warning("MAIN_ACTIVITY_HOST_CLASS_NAME not set — not running under Flet/Android?")
        return None
    try:
        from jnius import autoclass
        activity_host = autoclass(activity_host_class)
        _activity = activity_host.mActivity
        return _activity
    except Exception as e:
        logger.warning("Failed to get Android activity via jnius: %s", e)
        return None


def _ensure_jnius():
    global _PackageManager, _activity
    if _PackageManager is not None:
        return True
    try:
        from jnius import autoclass
    except ImportError:
        logger.warning("pyjnius not available — cannot resolve package names")
        return False

    activity = _get_activity()
    if activity is None:
        return False
    _PackageManager = activity.getPackageManager()
    return True


@lru_cache(maxsize=512)
def resolve(package_name: str) -> str:
    if package_name in _FALLBACK_NAMES:
        return _FALLBACK_NAMES[package_name]

    if not _ensure_jnius():
        return package_name

    try:
        info = _PackageManager.getApplicationInfo(package_name, 0)
        label = info.loadLabel(_PackageManager)
        if label:
            return str(label)
    except Exception:
        logger.debug("Could not resolve package: %s", package_name)

    return package_name

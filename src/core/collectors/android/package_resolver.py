import logging
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
_mActivity = None


def _ensure_jnius():
    global _PackageManager, _mActivity
    if _mActivity is not None:
        return True
    try:
        from jnius import autoclass
    except ImportError:
        return False
    _PythonActivity = autoclass("org.kivy.android.PythonActivity")
    _mActivity = _PythonActivity.mActivity
    _PackageManager = _mActivity.getPackageManager()
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

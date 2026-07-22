import logging
import os
import platform

_DATA_DIR_NAME = "TouchedGrassYet"
_ANDROID_PACKAGE = "com.mycompany.touched-grass-yet"

logger = logging.getLogger(__name__)


def get_data_dir() -> str:
    flet_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_data:
        return flet_data

    system = platform.system()
    if system == "Android":
        home = os.environ.get("HOME")
        if home:
            return os.path.join(home, _DATA_DIR_NAME)
        return os.path.join(f"/data/data/{_ANDROID_PACKAGE}/files", _DATA_DIR_NAME)
    if system == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            return os.path.join(base, _DATA_DIR_NAME)
    base = os.path.expanduser("~")
    return os.path.join(base, _DATA_DIR_NAME)


def get_export_dir() -> str:
    system = platform.system()
    if system == "Android":
        path = _android_export_dir()
    else:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
        path = os.path.join(docs, _DATA_DIR_NAME, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _android_export_dir() -> str:
    path = _android_public_downloads_dir()
    if path:
        return os.path.join(path, _DATA_DIR_NAME, "exports")
    path = _android_app_external_dir()
    if path:
        return os.path.join(path, _DATA_DIR_NAME, "exports")
    fallback = os.path.join(os.path.expanduser("~"), "Documents")
    return os.path.join(fallback, _DATA_DIR_NAME, "exports")


def _android_public_downloads_dir() -> str | None:
    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        dir_obj = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOWNLOADS
        )
        if dir_obj:
            return dir_obj.getAbsolutePath()
    except Exception:
        logger.warning("Failed to get public Downloads dir via jnius", exc_info=True)
    fallback = os.path.join("/storage", "emulated", "0", "Download")
    if os.path.isdir(fallback):
        return fallback
    return None


def _android_app_external_dir() -> str | None:
    try:
        from jnius import autoclass, cast
        Environment = autoclass("android.os.Environment")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        activity = cast("android.app.Activity", PythonActivity.mActivity)
        dir_obj = activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS)
        if dir_obj:
            return dir_obj.getAbsolutePath()
    except Exception:
        logger.warning("Failed to get app external Downloads dir via jnius", exc_info=True)
    return None

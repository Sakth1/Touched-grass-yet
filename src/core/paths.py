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
        docs = _android_documents_dir()
    else:
        docs = os.path.join(os.path.expanduser("~"), "Documents")
    if not docs:
        docs = os.path.expanduser("~")
    path = os.path.join(docs, _DATA_DIR_NAME, "exports")
    os.makedirs(path, exist_ok=True)
    return path


def _android_documents_dir() -> str | None:
    try:
        from jnius import autoclass
        Environment = autoclass("android.os.Environment")
        dir_obj = Environment.getExternalStoragePublicDirectory(
            Environment.DIRECTORY_DOCUMENTS
        )
        if dir_obj:
            return str(dir_obj)
    except Exception:
        logger.warning("Failed to get Android Documents dir via jnius", exc_info=True)
    fallback = "/storage/emulated/0/Documents"
    if os.path.isdir(fallback):
        return fallback
    return None

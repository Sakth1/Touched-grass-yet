import os
import platform

_DATA_DIR_NAME = "TouchedGrassYet"
_ANDROID_PACKAGE = "com.mycompany.touched-grass-yet"


def get_data_dir() -> str:
    system = platform.system()
    if system == "Android":
        home = os.environ.get("HOME")
        if home and os.access(home, os.W_OK):
            return os.path.join(home, _DATA_DIR_NAME)
        return os.path.join(f"/data/data/{_ANDROID_PACKAGE}/files", _DATA_DIR_NAME)
    if system == "Windows":
        base = os.environ.get("APPDATA")
        if base:
            return os.path.join(base, _DATA_DIR_NAME)
    base = os.path.expanduser("~")
    return os.path.join(base, _DATA_DIR_NAME)

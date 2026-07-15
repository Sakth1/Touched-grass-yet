import json
import os
import uuid
from functools import lru_cache

try:
    import winreg
except ImportError:
    winreg = None


def _machine_guid() -> str | None:
    if winreg is None:
        return None
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Cryptography",
        )
        guid = winreg.QueryValueEx(key, "MachineGuid")[0]
        winreg.CloseKey(key)
        return guid.strip()
    except Exception:
        return None


def _file_device_id() -> str:
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    config_dir = os.path.join(appdata, "TouchedGrassYet")
    device_file = os.path.join(config_dir, "device.json")
    os.makedirs(config_dir, exist_ok=True)

    if os.path.isfile(device_file):
        try:
            with open(device_file) as f:
                data = json.load(f)
            return data["device_id"]
        except Exception:
            pass

    new_id = str(uuid.uuid4())
    try:
        with open(device_file, "w") as f:
            json.dump({
                "device_id": new_id,
                "hostname": os.environ.get("COMPUTERNAME", ""),
            }, f)
    except Exception:
        pass
    return new_id


@lru_cache(maxsize=1)
def get_device_id() -> str:
    guid = _machine_guid()
    if guid:
        return guid
    return _file_device_id()

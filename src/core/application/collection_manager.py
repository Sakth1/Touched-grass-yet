import platform

from utils.models import SystemType, CollectionManager
from core.colllectors.android.android_collection_manager import AndroidCollectionManager
from core.colllectors.windows.windows_collection_manager import WindowsCollectionManager


class CollectionManager:
    def __init__(self):
        self.system_type: SystemType = SystemType.UNKNOWN
        self.collection_manager: CollectionManager | None = None

    def initiate(self):
        system_type = platform.system()
        match system_type:
            case "Windows":
                self.system_type = SystemType.WINDOWS
                self.collection_manager = WindowsCollectionManager()
            case "Android":
                self.system_type = SystemType.ANDROID
                self.collection_manager = AndroidCollectionManager()
            case _:
                self.system_type = SystemType.UNKNOWN

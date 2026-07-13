import platform

from utils.models import SystemType

class CollectionManager:
    def __init__(self):
        self.system_type: SystemType = None

    def initiate(self):
        system_type = platform.system()
        match system_type:
            case "Windows":
                self.system_type = SystemType.WINDOWS
            case "Android":
                self.system_type = SystemType.ANDROID
            case _:
                self.system_type = SystemType.UNKNOWN

        print(self.system_type)

if __name__ == "__main__":
    manager = CollectionManager()
    manager.initiate()
from . import system


class WindowsCollectionManager:
    def __init__(self) -> None:
        pass

    def start_collection(self) -> None:
        print(system.get_system_info())

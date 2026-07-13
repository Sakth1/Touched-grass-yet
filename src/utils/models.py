from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias, Union


class WindowsCollectionManager:
    pass


class AndroidCollectionManager:
    pass


CollectionManager: TypeAlias = Union[WindowsCollectionManager, AndroidCollectionManager]


@dataclass
class WindowsSystemInfo:
    OS: str
    Release: str
    Version: str
    Platform: str
    Machine: str
    Architecture: str
    Processor: str
    Node: str
    Hostname: str
    CurrentUser: str
    CurrentDirectory: str
    CurrentTime: str
    UTC: str
    BootTime: str


class SystemType(Enum):
    UNKNOWN = 0
    WINDOWS = 1
    ANDROID = 2

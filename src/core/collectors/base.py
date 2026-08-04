from typing import Optional, Protocol

from utils.models import Tick, WatcherConfig


class Watcher(Protocol):
    config: WatcherConfig

    def __init__(self, config: Optional[WatcherConfig] = None) -> None: ...
    async def tick(self) -> Tick | None: ...

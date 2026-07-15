from typing import Protocol

from utils.models import Tick, WatcherConfig


class Watcher(Protocol):
    config: WatcherConfig

    async def tick(self) -> Tick | None: ...

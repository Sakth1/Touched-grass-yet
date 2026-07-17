import asyncio
import logging

from core.collectors.base import Watcher
from core.tick_bus import TickBus

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self, bus: TickBus):
        self._bus = bus
        self._watchers: list[Watcher] = []
        self._tasks: list[asyncio.Task] = []
        self._running = False

    def register(self, watcher: Watcher) -> None:
        self._watchers.append(watcher)

    async def start(self) -> None:
        self._running = True
        for w in self._watchers:
            task = asyncio.create_task(self._run_loop(w))
            self._tasks.append(task)

    async def _run_loop(self, watcher: Watcher) -> None:
        cfg = watcher.config
        logger.info("Starting watcher %s (every %ss)", cfg.name, cfg.interval_s)
        while self._running:
            try:
                tick = await watcher.tick()
                if tick is not None:
                    await self._bus.send(tick)
            except Exception:
                logger.exception("Watcher %s failed", cfg.name)
            await asyncio.sleep(cfg.interval_s)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._watchers.clear()

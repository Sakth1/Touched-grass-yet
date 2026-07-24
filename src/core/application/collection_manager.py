import asyncio
import logging
import platform
from collections.abc import Callable

from core.config_manager import ConfigManager
from core.scheduler import Scheduler
from core.storage import Storage
from core.tick_bus import TickBus
from utils.models import Observation, SystemType, Tick

logger = logging.getLogger(__name__)

_OBSERVATION_TYPES: dict[str, str] = {
    "foreground": "event",
    "android_foreground": "event",
    "afk": "snapshot",
    "android_afk": "snapshot",
    "power": "state",
    "android_power": "state",
}


class _ObservationBridge:
    def __init__(self, storage: Storage):
        self._storage = storage

    def __call__(self, tick: Tick) -> None:
        obs = Observation(
            timestamp=tick.timestamp,
            watcher=tick.watcher,
            data=tick.data,
            observation_type=_OBSERVATION_TYPES.get(tick.watcher, "snapshot"),
        )
        self._storage.on_observation(obs)


class CollectionManager:
    def __init__(self, config: ConfigManager | None = None):
        self._config = config or ConfigManager()
        self._config.load()
        self._bus = TickBus()
        self._scheduler = Scheduler(self._bus)
        self._storage = Storage()
        self._runtime = None
        self._system_type = SystemType.UNKNOWN
        self._running = False
        self._auto_paused = False
        self._screen_monitor_task: asyncio.Task | None = None
        self._on_pause_changed = None
        self._obs_bridge = _ObservationBridge(self._storage)

    def detect_platform(self) -> SystemType:
        system = platform.system()
        match system:
            case "Windows":
                return SystemType.WINDOWS
            case "Android" | "Linux":
                return SystemType.ANDROID
            case _:
                return SystemType.UNKNOWN

    def _create_runtime(self):
        match self._system_type:
            case SystemType.WINDOWS:
                from core.collectors.windows.runtime import WindowsRuntime
                return WindowsRuntime(self._config)
            case SystemType.ANDROID:
                from core.collectors.android.runtime import AndroidRuntime
                return AndroidRuntime(self._config)
            case _:
                raise RuntimeError(f"Unsupported platform: {self._system_type}")

    async def start(self) -> None:
        self._system_type = self.detect_platform()
        logger.info("Detected platform: %s", self._system_type)

        self._bus.subscribe(self._storage.on_tick)
        self._bus.subscribe(self._obs_bridge)

        self._runtime = self._create_runtime()

        watchers = self._runtime.create_watchers()
        for w in watchers:
            self._scheduler.register(w)
            logger.info("Registered watcher: %s", w.config.name)

        await self._scheduler.start()
        self._running = True

        if not self._config.collection_enabled:
            self._scheduler.pause()
            logger.info("Collection started in paused state (from saved config)")

        if self._system_type == SystemType.ANDROID:
            self._screen_monitor_task = asyncio.create_task(self._monitor_screen_state())
            logger.info("Screen state monitor started")

        logger.info("Collection started")

    async def stop(self) -> None:
        self._running = False
        self._auto_paused = False
        if self._screen_monitor_task:
            self._screen_monitor_task.cancel()
            try:
                await self._screen_monitor_task
            except asyncio.CancelledError:
                pass
            self._screen_monitor_task = None
        await self._scheduler.stop()
        if self._runtime:
            self._runtime.shutdown()
        self._bus.unsubscribe(self._storage.on_tick)
        self._bus.unsubscribe(self._obs_bridge)
        logger.info("Collection stopped")

    def pause(self) -> None:
        if self._scheduler.is_paused:
            return
        self._auto_paused = False
        self._set_paused(True)

    def resume(self) -> None:
        if not self._scheduler.is_paused:
            return
        self._auto_paused = False
        self._set_paused(False)

    @property
    def is_paused(self) -> bool:
        return self._scheduler.is_paused

    def _set_paused(self, paused: bool) -> None:
        if paused:
            self._config.collection_enabled = False
            self._config.save()
            self._scheduler.pause()
        else:
            self._config.collection_enabled = True
            self._config.save()
            self._scheduler.resume()
        if self._on_pause_changed:
            self._on_pause_changed(paused)

    async def _monitor_screen_state(self, interval: float = 5.0) -> None:
        from core.collectors.android.usage_stats import is_screen_on

        was_on = is_screen_on()
        while self._running:
            await asyncio.sleep(interval)
            if not self._running:
                break
            now_on = is_screen_on()
            if was_on and not now_on:
                self._auto_paused = True
                self._set_paused(True)
                logger.info("Screen turned off — collection auto-paused")
            elif not was_on and now_on and self._auto_paused:
                self._auto_paused = False
                self._set_paused(False)
                logger.info("Screen turned on — collection auto-resumed")
            was_on = now_on

    @property
    def bus(self) -> TickBus:
        return self._bus

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def system_type(self) -> SystemType:
        return self._system_type

    @property
    def storage(self) -> Storage:
        return self._storage

    @property
    def on_pause_changed(self) -> Callable[[bool], None] | None:
        return self._on_pause_changed

    @on_pause_changed.setter
    def on_pause_changed(self, callback: Callable[[bool], None] | None) -> None:
        self._on_pause_changed = callback

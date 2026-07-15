import logging
import platform

from utils.models import SystemType
from core.tick_bus import TickBus
from core.scheduler import Scheduler
from core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class CollectionManager:
    def __init__(self, config: ConfigManager | None = None):
        self._config = config or ConfigManager()
        self._config.load()
        self._bus = TickBus()
        self._scheduler = Scheduler(self._bus)
        self._runtime = None
        self._system_type = SystemType.UNKNOWN
        self._running = False

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

        self._runtime = self._create_runtime()

        watchers = self._runtime.create_watchers()
        for w in watchers:
            self._scheduler.register(w)
            logger.info("Registered watcher: %s", w.config.name)

        await self._scheduler.start()
        self._running = True
        logger.info("Collection started")

    async def stop(self) -> None:
        self._running = False
        await self._scheduler.stop()
        if self._runtime:
            self._runtime.shutdown()
        logger.info("Collection stopped")

    @property
    def bus(self) -> TickBus:
        return self._bus

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def system_type(self) -> SystemType:
        return self._system_type

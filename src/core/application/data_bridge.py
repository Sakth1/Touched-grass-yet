import asyncio
import contextlib
import logging

from core.application.collection_manager import CollectionManager
from UI.services.state import AppState, AppSummary, CollectionStatus

logger = logging.getLogger(__name__)


class DataBridge:
    def __init__(self, manager: CollectionManager, state: AppState) -> None:
        self._manager = manager
        self._state = state
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        self._manager.on_pause_changed = self._on_pause_changed
        self._state.collection_status = CollectionStatus.RUNNING
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("DataBridge started")

    async def stop(self) -> None:
        self._manager.on_pause_changed = None
        self._state.collection_status = CollectionStatus.STOPPED
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("DataBridge stopped")

    def _on_pause_changed(self, paused: bool) -> None:
        self._state.collection_status = (
            CollectionStatus.PAUSED if paused else CollectionStatus.RUNNING
        )

    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(self._state.collection_interval_s)

            try:
                storage = self._manager.storage

                self._state.today_seconds = storage.get_today_seconds()

                battery = storage.get_latest_battery()
                if battery:
                    self._state.battery_pct = battery.get("level")
                    self._state.battery_charging = battery.get("charging")

                apps = storage.get_today_top_apps(limit=5)
                self._state.top_apps = [
                    AppSummary(
                        app_key=a["app_key"],
                        total_seconds=round(a["duration_s"], 1),
                        session_count=0,
                    )
                    for a in apps
                ]
            except Exception:
                logger.exception("DataBridge poll cycle failed")

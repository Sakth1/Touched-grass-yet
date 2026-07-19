import logging

import psutil

from utils.models import Tick, WatcherConfig

logger = logging.getLogger(__name__)


class PowerWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="power",
            interval_s=60.0,
            enabled=True,
        )

    async def tick(self) -> Tick | None:
        try:
            battery = psutil.sensors_battery()
            if battery is None:
                return Tick(
                    watcher="power",
                    data={
                        "battery_pct": None,
                        "charging": None,
                    },
                )
            return Tick(
                watcher="power",
                data={
                    "battery_pct": battery.percent,
                    "charging": bool(battery.power_plugged),
                },
            )
        except Exception:
            logger.exception("PowerWatcher tick failed")
            return Tick(
                watcher="power",
                data={"battery_pct": None, "charging": None},
            )

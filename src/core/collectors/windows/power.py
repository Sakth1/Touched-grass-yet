import psutil

from utils.models import Tick, WatcherConfig


class PowerWatcher:
    def __init__(self, config: WatcherConfig | None = None):
        self.config = config or WatcherConfig(
            name="power",
            interval_s=60.0,
            enabled=True,
        )

    async def tick(self) -> Tick | None:
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

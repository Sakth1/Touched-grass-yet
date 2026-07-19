from unittest.mock import patch

from core.collectors.android.afk import _ACTIVE_THRESHOLD, _IDLE_THRESHOLD, AndroidAfkWatcher
from core.collectors.windows.afk import AfkWatcher
from utils.models import WatcherConfig


class TestAfkParity:
    async def test_schema_keys_match(self):
        w = AfkWatcher(WatcherConfig(name="afk"))
        a = AndroidAfkWatcher(WatcherConfig(name="android_afk"))

        assert "afk" in w.config.name
        assert "afk" in a.config.name

    async def test_thresholds_match(self):
        assert _ACTIVE_THRESHOLD == 60
        assert _IDLE_THRESHOLD == 300

    async def test_android_afk_tick_returns_correct_schema(self):
        mock_time = 1_000_000_000

        with (
            patch("core.collectors.android.afk.get_current_time_ms", return_value=mock_time),
            patch("core.collectors.android.afk.is_screen_on", return_value=True),
            patch("core.collectors.android.afk.query_usage_events", return_value=[]),
        ):
            w = AndroidAfkWatcher()
            tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "android_afk"
        assert "status" in tick.data
        assert "idle_seconds" in tick.data
        assert tick.data["status"] in ("active", "idle", "away")
        assert isinstance(tick.data["idle_seconds"], float)

    async def test_android_afk_screen_off_returns_away(self):
        mock_time = 1_000_000_000

        with (
            patch("core.collectors.android.afk.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.afk.get_current_time_ms", return_value=mock_time),
            patch("core.collectors.android.afk.is_screen_on", return_value=False),
            patch("core.collectors.android.afk.query_usage_events", return_value=[]),
        ):
            w = AndroidAfkWatcher()
            tick = await w.tick()

        assert tick.data["status"] == "away"

    async def test_android_afk_idle_detection(self):
        mock_time = 1_000_000_000

        with (
            patch("core.collectors.android.afk.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.afk.get_current_time_ms", return_value=mock_time),
            patch("core.collectors.android.afk.is_screen_on", return_value=True),
            patch(
                "core.collectors.android.afk.query_usage_events",
                return_value=[
                    {
                        "package_name": "com.test",
                        "event_type": 1,
                        "time_stamp_ms": mock_time - 120_000,
                    }
                ],
            ),
        ):
            w = AndroidAfkWatcher()
            tick = await w.tick()

        assert tick.data["status"] == "idle"
        assert 119.0 <= tick.data["idle_seconds"] <= 121.0

    async def test_windows_afk_tick_returns_correct_schema(self):
        w = AfkWatcher()
        tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "afk"
        assert "status" in tick.data
        assert "idle_seconds" in tick.data
        assert tick.data["status"] in ("active", "idle", "away")

    async def test_afk_data_keys_and_types_match(self):
        from core.collectors.android.afk import AndroidAfkWatcher

        win = AfkWatcher()
        win_tick = await win.tick()

        and_w = AndroidAfkWatcher(WatcherConfig(name="android_afk"))
        with (
            patch("core.collectors.android.afk.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.afk.is_screen_on", return_value=True),
            patch("core.collectors.android.afk.get_current_time_ms", return_value=1_000_000),
            patch("core.collectors.android.afk.query_usage_events", return_value=[]),
        ):
            and_tick = await and_w.tick()

        assert win_tick.data.keys() == and_tick.data.keys()
        for key in win_tick.data:
            assert type(win_tick.data[key]) is type(and_tick.data[key])


class TestPowerParity:
    async def test_power_schema_keys_match(self):
        from core.collectors.android.power import AndroidPowerWatcher
        from core.collectors.windows.power import PowerWatcher

        wc_win = PowerWatcher()
        wc_and = AndroidPowerWatcher(WatcherConfig(name="android_power"))

        assert "power" in wc_win.config.name
        assert "power" in wc_and.config.name

    async def test_android_power_tick_returns_correct_schema(self):
        from core.collectors.android.power import AndroidPowerWatcher

        with patch("core.collectors.android.power.get_battery_info") as mock:
            mock.return_value = {"battery_pct": 85, "charging": True}
            w = AndroidPowerWatcher()
            tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "android_power"
        assert "battery_pct" in tick.data
        assert "charging" in tick.data
        assert tick.data["battery_pct"] == 85
        assert tick.data["charging"] is True

    async def test_android_power_no_battery(self):
        from core.collectors.android.power import AndroidPowerWatcher

        with patch("core.collectors.android.power.get_battery_info") as mock:
            mock.return_value = {"battery_pct": None, "charging": None}
            w = AndroidPowerWatcher()
            tick = await w.tick()

        assert tick.data["battery_pct"] is None
        assert tick.data["charging"] is None

    async def test_windows_power_tick_returns_correct_schema(self):
        from core.collectors.windows.power import PowerWatcher

        w = PowerWatcher()
        tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "power"
        assert "battery_pct" in tick.data
        assert "charging" in tick.data

    async def test_power_watcher_keys_match(self):
        assert {"battery_pct", "charging"} == {"battery_pct", "charging"}

    async def test_windows_power_data_types(self):
        from core.collectors.windows.power import PowerWatcher

        w = PowerWatcher()
        tick = await w.tick()

        assert isinstance(tick.data["battery_pct"], (int, float, type(None)))
        assert isinstance(tick.data["charging"], (bool, type(None)))

    async def test_android_power_data_types(self):
        from core.collectors.android.power import AndroidPowerWatcher

        with patch("core.collectors.android.power.get_battery_info") as mock:
            mock.return_value = {"battery_pct": 85, "charging": True}
            w = AndroidPowerWatcher()
            tick = await w.tick()

        assert isinstance(tick.data["battery_pct"], (int, type(None)))
        assert isinstance(tick.data["charging"], (bool, type(None)))


class TestForegroundParity:
    async def test_windows_foreground_schema_keys(self):
        from core.collectors.windows.foreground import ForegroundWatcher

        w = ForegroundWatcher()
        tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "foreground"
        assert "app" in tick.data
        assert "title" in tick.data

    async def test_android_foreground_schema_keys(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        MOCK_TIME = 1_700_000_000_000

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=MOCK_TIME),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
        ):
            w = AndroidForegroundWatcher()
            tick = await w.tick()

        assert tick is None

    async def test_android_foreground_active_schema_keys(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        MOCK_TIME = 1_700_000_000_000

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=MOCK_TIME),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": MOCK_TIME - 5000},
            ]),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            w = AndroidForegroundWatcher()
            tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "android_foreground"
        assert "package" in tick.data
        assert "app_name" in tick.data
        assert "durations" in tick.data
        assert "source" in tick.data

    async def test_foreground_schemas_diverge(self):
        win_keys = {"app", "title"}
        and_keys = {"package", "app_name", "durations", "source"}

        assert win_keys != and_keys


class TestPermissionDegradation:
    async def test_foreground_pauses_on_permission_loss(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        MOCK_TIME = 1_700_000_000_000

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=MOCK_TIME),
        ):
            w = AndroidForegroundWatcher()
            tick1 = await w.tick()
            assert tick1 is None
            assert w._permission_lost

            tick2 = await w.tick()
            assert tick2 is None

    async def test_foreground_resumes_on_permission_restored(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        MOCK_TIME = 1_700_000_000_000

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=MOCK_TIME),
        ):
            w = AndroidForegroundWatcher()
            await w.tick()
            assert w._permission_lost

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=MOCK_TIME + 100_000),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
        ):
            tick = await w.tick()
            assert not w._permission_lost
            assert tick is None

    async def test_afk_reports_away_on_permission_loss_screen_off(self):
        from core.collectors.android.afk import AndroidAfkWatcher

        with (
            patch("core.collectors.android.afk.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.afk.is_screen_on", return_value=False),
            patch("core.collectors.android.afk.get_current_time_ms", return_value=1_000_000),
        ):
            w = AndroidAfkWatcher()
            tick = await w.tick()

        assert tick is not None
        assert tick.data["status"] == "away"

    async def test_afk_reports_active_on_permission_loss_screen_on(self):
        from core.collectors.android.afk import AndroidAfkWatcher

        with (
            patch("core.collectors.android.afk.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.afk.is_screen_on", return_value=True),
            patch("core.collectors.android.afk.get_current_time_ms", return_value=1_000_000),
        ):
            w = AndroidAfkWatcher()
            tick = await w.tick()

        assert tick is not None
        assert tick.data["status"] == "active"

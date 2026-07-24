from unittest.mock import patch

_MS_PER_S = 1000
_60S = 60 * _MS_PER_S


class TestInitialization:
    BASE_TIME = 1_700_000_000_000

    async def test_first_tick_initializes_and_returns_none(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
        ):
            w = AndroidForegroundWatcher()
            tick = await w.tick()

        assert tick is None
        assert w._initialized is False

    async def test_first_tick_initializes_from_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME - 5000},
                ],
            ),
        ):
            w = AndroidForegroundWatcher()
            tick = await w.tick()

        assert tick is None
        assert w._current_app == "com.test.app"
        assert w._initialized is True

    async def test_first_tick_falls_back_to_stats(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = {
                "com.top.app": {
                    "package_name": "com.top.app",
                    "total_time_foreground_ms": 500000,
                    "last_time_used_ms": 100000,
                    "first_time_used_ms": 50000,
                    "app_name": "Top App",
                },
                "com.other.app": {
                    "package_name": "com.other.app",
                    "total_time_foreground_ms": 100000,
                    "last_time_used_ms": 50000,
                    "first_time_used_ms": 10000,
                    "app_name": "Other App",
                },
            }
            w = AndroidForegroundWatcher()
            tick = await w.tick()

        assert tick is None
        assert w._current_app == "com.top.app"
        assert w._initialized is True


class TestTransition:
    BASE_TIME = 1_700_000_000_000

    async def test_same_app_no_transition(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME - 5000},
                ],
            ),
        ):
            w = AndroidForegroundWatcher()
            await w.tick()

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
                ],
            ),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            tick = await w.tick()

        assert tick is None

    async def test_app_change_emits_transition(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.app1", "event_type": 1, "time_stamp_ms": self.BASE_TIME - 5000},
                ],
            ),
        ):
            w = AndroidForegroundWatcher()
            await w.tick()

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.app2", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
                ],
            ),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "android_foreground"
        assert tick.data["package"] == "com.app2"
        assert "app_name" in tick.data
        assert w._current_app == "com.app2"

    async def test_transition_data_has_correct_keys(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher()
        w._current_app = "com.old.app"
        w._last_tick_ms = self.BASE_TIME
        w._initialized = True

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch(
                "core.collectors.android.foreground.query_usage_events",
                return_value=[
                    {"package_name": "com.new.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
                ],
            ),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            tick = await w.tick()

        assert tick.data.keys() == {"package", "app_name"}
        assert "durations" not in tick.data
        assert "source" not in tick.data


class TestScreenAndIdle:
    BASE_TIME = 1_700_000_000_000

    async def test_stale_app_when_screen_on_and_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher()
        w._current_app = "com.last.app"
        w._last_tick_ms = self.BASE_TIME
        w._initialized = True

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            tick = await w.tick()

        assert tick is None
        assert w._current_app == "com.last.app"

    async def test_idle_when_screen_off_and_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher()
        w._current_app = "com.last.app"
        w._last_tick_ms = self.BASE_TIME
        w._initialized = True

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=False),
        ):
            tick = await w.tick()

        assert tick is None

    async def test_idle_when_no_previous_app_and_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher()
        w._current_app = None
        w._last_tick_ms = self.BASE_TIME
        w._initialized = True

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            tick = await w.tick()

        assert tick is None


class TestPermission:
    BASE_TIME = 1_700_000_000_000

    async def test_pauses_on_permission_loss(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
        ):
            w = AndroidForegroundWatcher()
            tick1 = await w.tick()
            assert tick1 is None
            assert w._permission_lost

            tick2 = await w.tick()
            assert tick2 is None

    async def test_resumes_on_permission_restored(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
        ):
            w = AndroidForegroundWatcher()
            await w.tick()
            assert w._permission_lost

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 100_000),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
        ):
            tick = await w.tick()
            assert not w._permission_lost
            assert tick is None

    async def test_clears_state_on_permission_loss(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher()
        w._current_app = "com.test.app"
        w._last_tick_ms = self.BASE_TIME
        w._initialized = True

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + 10_000),
        ):
            tick = await w.tick()

        assert tick is None
        assert w._current_app is None
        assert w._last_tick_ms is None
        assert w._initialized is False

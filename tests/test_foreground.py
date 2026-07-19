from unittest.mock import patch

from utils.models import WatcherConfig

_MS_PER_S = 1000
_60S = 60 * _MS_PER_S
_BUFFER_MS = 2_000


class TestMultiTickAccumulation:
    BASE_TIME = 1_700_000_000_000

    def _advance(self, offset_s: float) -> int:
        return self.BASE_TIME + int(offset_s * _MS_PER_S)

    async def test_single_session_crosses_tick_boundary(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        RESUMED_AT_S = 5
        PAUSED_AT_S = 58
        TICK1 = 60
        TICK2 = 120

        resumed_ms = self._advance(RESUMED_AT_S)
        paused_ms = self._advance(PAUSED_AT_S)

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self._advance(0)

        with (
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": resumed_ms},
            ]
            dur1, pkg1, src1 = w._try_events(self._advance(TICK1))
            assert pkg1 == "com.test.app"
            reported_tick1 = dur1.get("com.test.app", 0)
            assert reported_tick1 > 0

            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": resumed_ms},
                {"package_name": "com.test.app", "event_type": 2, "time_stamp_ms": paused_ms},
            ]
            dur2, pkg2, src2 = w._try_events(self._advance(TICK2))
            reported_tick2 = dur2.get("com.test.app", 0)

        total = reported_tick1 + reported_tick2
        expected = (PAUSED_AT_S - RESUMED_AT_S) * _MS_PER_S
        assert abs(total - expected) <= _MS_PER_S, f"total={total}ms, expected={expected}ms"

    async def test_open_session_reported_each_tick(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        RESUMED_AT_S = 5

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self._advance(0)

        with (
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self._advance(RESUMED_AT_S)},
            ]

            dur1, pkg1, src1 = w._try_events(self._advance(60))
            assert pkg1 == "com.test.app"
            reported1 = dur1.get("com.test.app", 0)
            assert reported1 > 0

            dur2, pkg2, src2 = w._try_events(self._advance(120))
            assert pkg2 == "com.test.app"
            reported2 = dur2.get("com.test.app", 0)
            assert reported2 > 0

    async def test_session_reported_tracks_across_ticks(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        RESUMED_AT_S = 5

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self._advance(0)

        with (
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self._advance(RESUMED_AT_S)},
            ]

            w._try_events(self._advance(60))

            seg_key = ("com.test.app", self._advance(RESUMED_AT_S))
            assert seg_key in w._session_reported
            assert w._session_reported[seg_key] > 0

    async def test_stale_session_reported_cleanup(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self._advance(0)
        w._session_reported[("com.stale", 1000)] = 500

        with (
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
        ):
            w._try_events(self._advance(60))
            assert ("com.stale", 1000) not in w._session_reported

    async def test_session_reported_cleared_on_permission_loss(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._session_reported[("com.test", 1000)] = 500
        w._last_tick_ms = self._advance(0)
        w._previous_app = "com.test"

        with patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=False):
            tick = await w.tick()

        assert tick is None
        assert len(w._session_reported) == 0
        assert len(w._active_events) == 0
        assert len(w._last_foreground_ms) == 0

    async def test_events_returns_without_double_count(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        RESUMED_AT_S = 5
        PAUSED_AT_S = 58
        RESUMED2_AT_S = 70

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self._advance(0)

        with (
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
        ):
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self._advance(RESUMED_AT_S)},
            ]
            w._try_events(self._advance(60))

            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 2, "time_stamp_ms": self._advance(PAUSED_AT_S)},
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self._advance(RESUMED2_AT_S)},
            ]
            dur2, pkg2, src2 = w._try_events(self._advance(120))

            assert ("com.test.app", self._advance(RESUMED_AT_S)) not in w._session_reported

            reported2 = dur2.get("com.test.app", 0)
            assert reported2 > 0


class TestFirstTick:
    BASE_TIME = 1_700_000_000_000

    async def test_previous_app_from_stats_when_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.query_usage_stats") as mock_stats,
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME),
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
            tick = await w.tick()

        assert tick is None
        assert w._previous_app == "com.top.app"


class TestScreenOnFallback:
    BASE_TIME = 1_700_000_000_000

    async def test_keeps_previous_app_when_screen_on(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME
        w._previous_app = "com.last.app"

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + _60S),
        ):
            tick = await w.tick()

        assert tick is not None
        assert tick.data["package"] == "com.last.app"
        assert tick.data["source"] == "stale"

    async def test_idle_when_screen_off_and_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=False),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + _60S),
        ):
            tick = await w.tick()

        assert tick is None

    async def test_idle_when_no_previous_app_and_no_events(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.query_usage_events", return_value=[]),
            patch("core.collectors.android.foreground.query_usage_stats", return_value={}),
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms", return_value=self.BASE_TIME + _60S),
        ):
            tick = await w.tick()

        assert tick is None


class TestStatsSync:
    BASE_TIME = 1_700_000_000_000

    async def test_sync_updates_last_foreground_ms(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME

        with (
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.query_usage_stats") as mock_stats,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
        ):
            mock_stats.return_value = {
                "com.test.app": {
                    "package_name": "com.test.app",
                    "total_time_foreground_ms": 100000,
                    "last_time_used_ms": 100000,
                    "first_time_used_ms": 50000,
                    "app_name": "Test App",
                },
            }
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
            ]

            w._try_events(self.BASE_TIME + _60S)

            assert w._last_foreground_ms.get("com.test.app") == 100000

            mock_stats.return_value = {
                "com.test.app": {
                    "package_name": "com.test.app",
                    "total_time_foreground_ms": 101000,
                    "last_time_used_ms": 101000,
                    "first_time_used_ms": 50000,
                    "app_name": "Test App",
                },
            }
            mock_events.return_value = []

            w._try_events(self.BASE_TIME + 2 * _60S)

            assert w._last_foreground_ms.get("com.test.app") == 101000

    async def test_sync_updates_all_packages(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME

        def make_stats(pkg1_time, pkg2_time):
            return {
                "com.pkg1": {"package_name": "com.pkg1", "total_time_foreground_ms": pkg1_time,
                             "last_time_used_ms": pkg1_time, "first_time_used_ms": 10000, "app_name": "Pkg1"},
                "com.pkg2": {"package_name": "com.pkg2", "total_time_foreground_ms": pkg2_time,
                             "last_time_used_ms": pkg2_time, "first_time_used_ms": 5000, "app_name": "Pkg2"},
            }

        with (
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.query_usage_stats") as mock_stats,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground._build_result", side_effect=lambda d: d),
        ):
            mock_stats.side_effect = [make_stats(50000, 30000), make_stats(50100, 30000)]
            mock_events.return_value = [
                {"package_name": "com.pkg1", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
            ]

            w._try_events(self.BASE_TIME + _60S)
            assert w._last_foreground_ms.get("com.pkg1") == 50000
            assert w._last_foreground_ms.get("com.pkg2") == 30000

            w._try_events(self.BASE_TIME + 2 * _60S)
            assert w._last_foreground_ms.get("com.pkg1") == 50100
            assert w._last_foreground_ms.get("com.pkg2") == 30000

    async def test_sync_prevents_huge_stats_fallback_deltas(self):
        from core.collectors.android.foreground import AndroidForegroundWatcher

        w = AndroidForegroundWatcher(WatcherConfig(name="android_foreground", interval_s=60.0))
        w._last_tick_ms = self.BASE_TIME

        with (
            patch("core.collectors.android.foreground.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.foreground.query_usage_events") as mock_events,
            patch("core.collectors.android.foreground.query_usage_stats") as mock_stats,
            patch("core.collectors.android.foreground.is_screen_on", return_value=True),
            patch("core.collectors.android.foreground.get_current_time_ms") as mock_time,
        ):
            def make_stats(total_ms):
                return {"com.test.app": {"package_name": "com.test.app",
                    "total_time_foreground_ms": total_ms, "last_time_used_ms": total_ms,
                    "first_time_used_ms": 50000, "app_name": "Test App",
                }}

            mock_stats.return_value = make_stats(100000)
            mock_time.return_value = self.BASE_TIME

            init_tick = await w.tick()
            assert init_tick is None

            mock_time.return_value = self.BASE_TIME + _60S
            mock_events.return_value = [
                {"package_name": "com.test.app", "event_type": 1, "time_stamp_ms": self.BASE_TIME + 5000},
            ]

            tick1 = await w.tick()
            assert tick1 is not None

            assert w._last_foreground_ms.get("com.test.app") == 100000

            mock_time.return_value = self.BASE_TIME + 2 * _60S
            mock_events.return_value = []
            mock_stats.return_value = make_stats(101000)

            tick2 = await w.tick()

            assert tick2 is not None
            assert tick2.data["source"] == "stale"
            assert len(tick2.data["durations"]) == 0

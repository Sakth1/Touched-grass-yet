from unittest.mock import patch


class TestAppUsageInitialization:
    BASE_TIME = 1_700_000_000_000

    async def test_first_tick_initializes_and_returns_none(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = {
                "com.pkg1": {
                    "package_name": "com.pkg1",
                    "total_time_foreground_ms": 100000,
                    "last_time_used_ms": 100000,
                    "first_time_used_ms": 50000,
                    "app_name": "Pkg1",
                },
            }
            w = AndroidAppUsageWatcher()
            tick = await w.tick()

        assert tick is None
        assert w._last_foreground_ms.get("com.pkg1") == 100000

    async def test_no_stats_on_first_tick(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats", return_value={}),
        ):
            w = AndroidAppUsageWatcher()
            tick = await w.tick()

        assert tick is None
        assert len(w._last_foreground_ms) == 0


class TestAppUsageInterval:
    BASE_TIME = 1_700_000_000_000

    def _make_stats(self, pkg: str, total_ms: int, app_name: str = "Test App") -> dict:
        return {
            pkg: {
                "package_name": pkg,
                "total_time_foreground_ms": total_ms,
                "last_time_used_ms": total_ms,
                "first_time_used_ms": 50000,
                "app_name": app_name,
            }
        }

    async def test_emits_intervals_for_active_packages(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._last_foreground_ms = {"com.pkg1": 100000}

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = self._make_stats("com.pkg1", 101000, "Pkg1")
            tick = await w.tick()

        assert tick is not None
        assert tick.watcher == "android_app_usage"
        assert "intervals" in tick.data
        assert len(tick.data["intervals"]) == 1
        assert tick.data["intervals"][0]["package"] == "com.pkg1"
        assert tick.data["intervals"][0]["duration_ms"] == 1000

    async def test_no_emission_for_no_delta(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._last_foreground_ms = {"com.pkg1": 100000}

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = self._make_stats("com.pkg1", 100000, "Pkg1")
            tick = await w.tick()

        assert tick is None

    async def test_emits_multiple_package_intervals(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._last_foreground_ms = {"com.pkg1": 100000, "com.pkg2": 50000}

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = {
                "com.pkg1": {
                    "package_name": "com.pkg1",
                    "total_time_foreground_ms": 102000,
                    "last_time_used_ms": 102000,
                    "first_time_used_ms": 50000,
                    "app_name": "Pkg1",
                },
                "com.pkg2": {
                    "package_name": "com.pkg2",
                    "total_time_foreground_ms": 50500,
                    "last_time_used_ms": 50500,
                    "first_time_used_ms": 10000,
                    "app_name": "Pkg2",
                },
            }
            tick = await w.tick()

        assert tick is not None
        assert len(tick.data["intervals"]) == 2
        pkg_map = {i["package"]: i["duration_ms"] for i in tick.data["intervals"]}
        assert pkg_map["com.pkg1"] == 2000
        assert pkg_map["com.pkg2"] == 500
        assert tick.data["intervals"][0]["duration_ms"] >= tick.data["intervals"][1]["duration_ms"]

    async def test_cleans_up_stale_packages(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._last_foreground_ms = {"com.stale": 100000, "com.active": 50000}

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = self._make_stats("com.active", 51000, "Active")
            tick = await w.tick()

        assert tick is not None
        assert "com.stale" not in w._last_foreground_ms
        assert len(tick.data["intervals"]) == 1
        assert tick.data["intervals"][0]["package"] == "com.active"

    async def test_pauses_on_permission_loss(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._last_foreground_ms = {"com.test": 100000}

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=False),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
        ):
            tick = await w.tick()

        assert tick is None
        assert w._permission_lost
        assert len(w._last_foreground_ms) == 0

    async def test_resumes_on_permission_restored(self):
        from core.collectors.android.app_usage import AndroidAppUsageWatcher

        w = AndroidAppUsageWatcher()
        w._permission_lost = True

        with (
            patch("core.collectors.android.app_usage.check_usage_stats_permission", return_value=True),
            patch("core.collectors.android.app_usage.get_current_time_ms", return_value=self.BASE_TIME),
            patch("core.collectors.android.app_usage.query_usage_stats") as mock_stats,
        ):
            mock_stats.return_value = self._make_stats("com.pkg1", 100000, "Pkg1")
            tick = await w.tick()

        assert not w._permission_lost
        assert tick is None
        assert w._last_foreground_ms.get("com.pkg1") == 100000

"""Lifecycle sweep: end-to-end collection wiring and headless UI boot.

Phase 4 of the QA overhaul. Exercises the real wiring — real ``TickBus``,
real ``Scheduler``, real ``Storage``, real event bridge — behind a fake
platform runtime, plus a headless ``App()`` boot across every
``ScreenFormFactor`` and its navigation paths. No hardcoded module or
function names beyond the classes under test.
"""

from __future__ import annotations

import asyncio
import logging
import time
from unittest.mock import patch

import flet as ft
from sweep_helpers import mock_page

from core.application.collection_manager import CollectionManager, _EventBridge
from core.config_manager import ConfigManager
from utils.models import OSType, ScreenFormFactor, Tick, WatcherConfig

_EVENT_TIMEOUT_S = 5.0


class _FakeWatcher:
    """Real watcher protocol, fake payloads — every tick emits real data."""

    def __init__(self, name: str, interval_s: float = 0.01):
        self.config = WatcherConfig(name=name, interval_s=interval_s)
        self.ticks = 0
        self._n = 0

    async def tick(self) -> Tick:
        self.ticks += 1
        self._n += 1
        return Tick(watcher=self.config.name, data={"app": f"App{self._n % 3}.exe"})


class _FakeRuntime:
    def __init__(self, watchers):
        self._watchers = watchers
        self.shutdown_calls = 0

    def create_watchers(self):
        return list(self._watchers)

    def shutdown(self) -> None:
        self.shutdown_calls += 1


async def _wait_for(predicate, timeout: float = _EVENT_TIMEOUT_S) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"condition not met within {timeout}s")


class TestEventBridge:
    def test_unknown_watcher_writes_nothing(self, in_memory_db):
        bridge = _EventBridge(in_memory_db, "windows")
        bridge(Tick(watcher="mystery", data={"app": "x"}))
        assert in_memory_db.get_raw_events() == []

    def test_foreground_transition_deduped(self, in_memory_db):
        bridge = _EventBridge(in_memory_db, "windows")
        bridge(Tick(watcher="foreground", data={"app": "Code.exe"}))
        bridge(Tick(watcher="foreground", data={"app": "Code.exe"}))
        assert len(in_memory_db.get_raw_events()) == 1

        bridge(Tick(watcher="foreground", data={"app": "Browser.exe"}))
        events = in_memory_db.get_raw_events()
        assert len(events) == 2
        assert events[0]["event_type"] == "foreground_transition"

    def test_app_usage_intervals_fan_out(self, in_memory_db):
        bridge = _EventBridge(in_memory_db, "android")
        bridge(
            Tick(
                watcher="android_app_usage",
                data={
                    "intervals": [{"app": "A", "start": 1}, {"app": "B", "start": 2}]
                },
            )
        )
        events = in_memory_db.get_raw_events()
        assert len(events) == 2
        assert all(e["event_type"] == "app_usage_interval" for e in events)
        assert events[0]["payload"]["app"] == "A"

    def test_other_watcher_types_mapped(self, in_memory_db):
        bridge = _EventBridge(in_memory_db, "windows")
        bridge(Tick(watcher="afk", data={"status": "idle"}))
        bridge(Tick(watcher="android_afk", data={"present": False}))
        bridge(Tick(watcher="power", data={"on_ac": True}))
        bridge(Tick(watcher="android_power", data={"on_ac": True}))
        types = {e["event_type"] for e in in_memory_db.get_raw_events()}
        assert types == {"idle_transition", "user_presence", "power_change"}


class TestCollectionEndToEnd:
    async def test_start_flows_ticks_into_storage(self, tmp_path):
        config = ConfigManager(path=str(tmp_path / "config.json"))
        cm = CollectionManager(config)
        runtime = _FakeRuntime([_FakeWatcher("foreground"), _FakeWatcher("afk")])
        with (
            patch(
                "core.application.collection_manager.detect_os",
                return_value=OSType.WINDOWS,
            ),
            patch.object(cm, "_create_runtime", return_value=runtime),
        ):
            await cm.start()

        try:
            assert cm.is_running
            assert cm.system_type is OSType.WINDOWS
            assert len(cm._scheduler._watchers) == 2

            await _wait_for(lambda: len(cm.storage.get_raw_events()) >= 2)

            events = cm.storage.get_raw_events()
            assert {e["event_type"] for e in events} >= {
                "foreground_transition",
                "idle_transition",
            }
        finally:
            await cm.stop()

        assert runtime.shutdown_calls == 1
        assert not cm.is_running
        assert cm._scheduler._tasks == []
        assert cm._health_monitor_task is None

    async def test_pause_halts_resume_restarts_flow(self, tmp_path):
        config = ConfigManager(path=str(tmp_path / "config.json"))
        cm = CollectionManager(config)
        runtime = _FakeRuntime([_FakeWatcher("afk")])
        with (
            patch(
                "core.application.collection_manager.detect_os",
                return_value=OSType.WINDOWS,
            ),
            patch.object(cm, "_create_runtime", return_value=runtime),
        ):
            await cm.start()

        try:
            await _wait_for(lambda: len(cm.storage.get_raw_events()) > 0)

            cm.pause()
            assert cm.is_paused
            assert not config.collection_enabled
            count_at_pause = len(cm.storage.get_raw_events())
            await asyncio.sleep(0.05)
            assert len(cm.storage.get_raw_events()) == count_at_pause

            cm.resume()
            assert not cm.is_paused
            assert config.collection_enabled
            await _wait_for(lambda: len(cm.storage.get_raw_events()) > count_at_pause)
        finally:
            await cm.stop()

    async def test_start_with_collection_disabled_auto_pauses(self, tmp_path):
        config = ConfigManager(path=str(tmp_path / "config.json"))
        config.collection_enabled = False
        config.save()
        cm = CollectionManager(config)
        runtime = _FakeRuntime([_FakeWatcher("afk")])
        with (
            patch(
                "core.application.collection_manager.detect_os",
                return_value=OSType.WINDOWS,
            ),
            patch.object(cm, "_create_runtime", return_value=runtime),
        ):
            await cm.start()

        try:
            assert cm.is_running
            assert cm.is_paused
            await asyncio.sleep(0.05)
            assert cm.storage.get_raw_events() == []
        finally:
            await cm.stop()

    async def test_stop_is_idempotent(self, tmp_path):
        cm = CollectionManager(ConfigManager(path=str(tmp_path / "config.json")))
        await cm.stop()
        await cm.stop()
        assert not cm.is_running
        assert cm._scheduler._tasks == []


class TestAppHeadlessBoot:
    @staticmethod
    def _page(width=None, height=None):
        page = mock_page()
        page.window.width = width
        page.window.height = height
        return page

    def test_desktop_boot(self):
        from app import App

        app = App(self._page(1280, 800))
        assert app.layout.screen_form_factor is ScreenFormFactor.DESKTOP
        assert app.navigation_rail is not None
        assert len(app.shell.controls) == 2
        assert app.page.navigation_bar is None

    def test_tablet_boot(self):
        from app import App

        app = App(self._page(960, 800))
        assert app.layout.screen_form_factor is ScreenFormFactor.TABLET
        assert app.page.navigation_bar is not None
        assert app.route_manager.current_route == "/dashboard"

    def test_mobile_boot(self):
        from app import App

        app = App(self._page(400, 800))
        assert app.layout.screen_form_factor is ScreenFormFactor.MOBILE
        assert app.page.navigation_bar is not None
        assert app.navigation_rail is None

    def test_navigate_every_route(self):
        from app import App

        app = App(self._page(1280, 800))
        for route, screen in (
            ("/dashboard", app.dashboard_page),
            ("/timeline", app.timeline_page),
            ("/analytics", app.analytics_page),
            ("/settings", app.settings_page),
        ):
            app.route_manager.navigate(route)
            assert app.content_container.content is screen
            assert app.route_manager.current_route == route

    def test_route_change_event_before_any_navigate(self):
        from app import App

        app = App(self._page(400, 800))
        event = ft.Event(name="routeChange", control=None)
        event.route = "/timeline"
        app.route_manager.handle_route_change(event)
        assert app.route_manager.current_route == "/timeline"
        assert app.content_container.content is app.timeline_page

    def test_navigation_bar_select_switches_view(self):
        from app import App

        app = App(self._page(400, 800))
        app.page.navigation_bar.select_index(2)
        assert app.content_container.content is app.analytics_page
        assert app.route_manager.current_route == "/analytics"

    def test_navigation_rail_select_switches_view(self):
        from app import App

        app = App(self._page(1280, 800))
        app.navigation_rail.select_index(1)
        assert app.content_container.content is app.timeline_page

    def test_rail_settings_trailing_click(self):
        from app import App

        app = App(self._page(1280, 800))
        on_click = app.navigation_rail.trailing.on_click
        assert on_click is not None
        on_click(None)  # type: ignore[reportCallIssue]
        assert app.content_container.content is app.settings_page
        assert app.route_manager.current_route == "/settings"

    def test_unknown_route_falls_back_to_home(self, caplog):
        from app import App

        app = App(self._page(1280, 800))
        with caplog.at_level(logging.WARNING, logger="UI.routing"):
            app.route_manager.navigate("/nope")
        assert "Unknown route" in caplog.text
        assert app.content_container.content is None
        assert app.route_manager.current_route == "/home"

    def test_resize_switches_form_factor(self):
        from app import App

        app = App(self._page(1280, 800))
        assert app.layout.screen_form_factor is ScreenFormFactor.DESKTOP

        page = app.page
        page.width = 400
        page.height = 800
        page.media = None
        page.navigation_bar = None
        app._handle_page_resize(None)
        assert app.layout.screen_form_factor is ScreenFormFactor.MOBILE
        assert page.navigation_bar is not None
        assert len(app.shell.controls) == 1

        page.width = 1280
        page.height = 800
        app._handle_page_resize(None)
        assert app.layout.screen_form_factor is ScreenFormFactor.DESKTOP
        assert page.navigation_bar is None
        assert len(app.shell.controls) == 2

    def test_alert_dialog_close_runs_callback(self):
        from UI.dialogs import show_alert_dialog

        page = mock_page()
        closed = []
        show_alert_dialog(page, "Title", "Message", on_close=lambda: closed.append(1))
        dialog = page.show_dialog.call_args.args[0]
        dialog.actions[0].on_click(None)
        assert closed == [1]
        page.pop_dialog.assert_called()

    def test_permission_dialog_shows(self):
        from UI.dialogs import show_permission_dialog

        page = mock_page()
        show_permission_dialog(page)
        page.show_dialog.assert_called_once()

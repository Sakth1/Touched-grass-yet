import asyncio
from unittest.mock import patch

from core.config_manager import ConfigManager
from core.scheduler import Scheduler
from core.tick_bus import TickBus


class TestPauseResume:
    async def test_pause_sets_flag_and_saves_config(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        config = ConfigManager(path=str(tmp_path / "config.json"))
        cm = CollectionManager(config)
        assert not cm.is_paused
        assert config.collection_enabled

        cm.pause()
        assert cm.is_paused
        assert not config.collection_enabled

        config.load()
        assert not config.collection_enabled

    async def test_resume_clears_flag_and_saves_config(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        config = ConfigManager(path=str(tmp_path / "config.json"))
        cm = CollectionManager(config)
        cm.pause()
        assert cm.is_paused

        cm.resume()
        assert not cm.is_paused
        assert config.collection_enabled

        config.load()
        assert config.collection_enabled

    async def test_pause_when_already_paused_is_noop(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm.pause()
        cm.pause()
        assert cm.is_paused

    async def test_resume_when_not_paused_is_noop(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm.resume()
        assert not cm.is_paused

    async def test_stop_clears_auto_paused(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm._auto_paused = True
        await cm.stop()
        assert not cm._auto_paused

    async def test_on_pause_changed_callback_fired(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        events = []
        cm = CollectionManager()
        cm.on_pause_changed = lambda p: events.append(p)

        cm.pause()
        cm.resume()

        assert events == [True, False]

    async def test_new_manager_from_saved_config_starts_paused(self, tmp_path):
        from core.application.collection_manager import CollectionManager

        config = ConfigManager(path=str(tmp_path / "config.json"))
        cm1 = CollectionManager(config)
        cm1.pause()

        config2 = ConfigManager(path=str(tmp_path / "config.json"))
        config2.load()
        assert not config2.collection_enabled

    async def test_is_paused_reflects_scheduler_state(self):
        s = Scheduler(TickBus())
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        assert cm.is_paused == s.is_paused

        s.pause()
        cm._scheduler = s
        assert cm.is_paused


class TestScreenMonitor:
    async def test_screen_off_triggers_auto_pause(self):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm._running = True

        with (
            patch("core.collectors.android.usage_stats.is_screen_on", side_effect=[True, False, False, False]),
        ):
            monitor = asyncio.create_task(cm._monitor_screen_state(interval=0.01))
            await asyncio.sleep(0.05)
            cm._running = False
            try:
                await monitor
            except asyncio.CancelledError:
                pass

        assert cm._auto_paused
        assert cm.is_paused

    async def test_screen_on_after_auto_pause_auto_resumes(self):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm._running = True
        cm._auto_paused = True
        cm._set_paused(True)

        with (
            patch("core.collectors.android.usage_stats.is_screen_on", side_effect=[False, True, True, True]),
        ):
            monitor = asyncio.create_task(cm._monitor_screen_state(interval=0.01))
            await asyncio.sleep(0.05)
            cm._running = False
            try:
                await monitor
            except asyncio.CancelledError:
                pass

        assert not cm._auto_paused
        assert not cm.is_paused

    async def test_user_pause_not_overridden_by_screen_on(self):
        from core.application.collection_manager import CollectionManager

        cm = CollectionManager()
        cm._running = True
        cm.pause()

        with (
            patch("core.collectors.android.usage_stats.is_screen_on", side_effect=[False, True, True, True]),
        ):
            monitor = asyncio.create_task(cm._monitor_screen_state(interval=0.01))
            await asyncio.sleep(0.05)
            cm._running = False
            try:
                await monitor
            except asyncio.CancelledError:
                pass

        assert cm.is_paused

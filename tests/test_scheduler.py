import asyncio

import pytest

from core.scheduler import Scheduler
from core.tick_bus import TickBus
from utils.models import Tick, WatcherConfig


class _CountingWatcher:
    def __init__(self, config: WatcherConfig, result: Tick | None = None):
        self.config = config
        self.result = result or Tick(watcher=config.name)
        self.tick_count = 0

    async def tick(self) -> Tick | None:
        self.tick_count += 1
        return self.result


class _CrashingWatcher:
    def __init__(self, config: WatcherConfig):
        self.config = config

    async def tick(self) -> Tick | None:
        raise RuntimeError("simulated watcher crash")


class _VariableReturnWatcher:
    def __init__(self, config: WatcherConfig, returns: list[Tick | None]):
        self.config = config
        self._returns = returns
        self._idx = 0

    async def tick(self) -> Tick | None:
        if self._idx < len(self._returns):
            val = self._returns[self._idx]
            self._idx += 1
            return val
        return None


@pytest.fixture
def bus():
    return TickBus()


@pytest.fixture
def scheduler(bus):
    return Scheduler(bus)


class TestSchedulerLifecycle:
    async def test_start_creates_task_per_watcher(self, scheduler):
        w1 = _CountingWatcher(WatcherConfig(name="fg", interval_s=0.01))
        w2 = _CountingWatcher(WatcherConfig(name="afk", interval_s=0.01))
        scheduler.register(w1)
        scheduler.register(w2)

        await scheduler.start()
        assert scheduler._running
        assert len(scheduler._tasks) == 2

        await scheduler.stop()

    async def test_stop_cancels_tasks_and_clears_state(self, scheduler):
        w = _CountingWatcher(WatcherConfig(name="fg", interval_s=0.01))
        scheduler.register(w)

        await scheduler.start()
        assert scheduler._running
        assert len(scheduler._tasks) == 1

        await scheduler.stop()
        assert not scheduler._running
        assert len(scheduler._tasks) == 0
        assert len(scheduler._watchers) == 0

    async def test_tasks_are_truly_done_after_stop(self, scheduler):
        w = _CountingWatcher(WatcherConfig(name="fg", interval_s=0.5))
        scheduler.register(w)

        await scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

        assert all(t.done() for t in scheduler._tasks)

    async def test_restart_after_stop(self, scheduler):
        w = _CountingWatcher(WatcherConfig(name="fg", interval_s=0.01))
        scheduler.register(w)

        await scheduler.start()
        await asyncio.sleep(0.05)
        before = w.tick_count
        await scheduler.stop()

        scheduler.register(w)
        await scheduler.start()
        await asyncio.sleep(0.05)
        assert w.tick_count > before

        await scheduler.stop()

    async def test_watcher_crash_does_not_kill_loop(self, scheduler):
        crashing = _CrashingWatcher(WatcherConfig(name="crash", interval_s=0.01))
        working = _CountingWatcher(WatcherConfig(name="working", interval_s=0.01))
        scheduler.register(crashing)
        scheduler.register(working)

        await scheduler.start()
        await asyncio.sleep(0.1)
        await scheduler.stop()

        assert working.tick_count > 0

    async def test_watcher_crash_does_not_stop_own_loop(self, scheduler):
        crash_count = 0

        class _CrashThenRecover:
            def __init__(self):
                self.config = WatcherConfig(name="crash_recover", interval_s=0.01)

            async def tick(self) -> Tick | None:
                nonlocal crash_count
                crash_count += 1
                if crash_count <= 3:
                    raise RuntimeError("transient failure")
                return Tick(watcher="crash_recover")

        w = _CrashThenRecover()
        scheduler.register(w)

        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()

        assert crash_count > 3

    async def test_tick_delivered_to_bus(self, scheduler, bus):
        received = []
        bus.subscribe(lambda t: received.append(t.watcher))

        w = _CountingWatcher(WatcherConfig(name="fg", interval_s=0.01))
        scheduler.register(w)
        await scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

        assert "fg" in received
        assert len(received) > 0

    async def test_multiple_watchers_independent_intervals(self, scheduler):
        fast = _CountingWatcher(WatcherConfig(name="fast", interval_s=0.01))
        slow = _CountingWatcher(WatcherConfig(name="slow", interval_s=0.05))
        scheduler.register(fast)
        scheduler.register(slow)

        await scheduler.start()
        await asyncio.sleep(0.15)
        await scheduler.stop()

        assert fast.tick_count >= 5
        assert slow.tick_count >= 1
        assert fast.tick_count > slow.tick_count

    async def test_watcher_returns_none_does_not_send_to_bus(self, scheduler, bus):
        received = []
        bus.subscribe(lambda t: received.append(t.watcher))

        w = _VariableReturnWatcher(
            WatcherConfig(name="fg", interval_s=0.01),
            returns=[None, Tick(watcher="fg"), None, Tick(watcher="fg")],
        )
        scheduler.register(w)
        await scheduler.start()
        await asyncio.sleep(0.05)
        await scheduler.stop()

        assert len(received) < w._idx

    async def test_stop_without_start(self, scheduler):
        await scheduler.stop()
        assert not scheduler._running
        assert len(scheduler._tasks) == 0

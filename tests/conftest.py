import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from core.tick_bus import TickBus
from utils.models import Tick, WatcherConfig


@pytest.fixture(autouse=True, scope="session")
def patch_device_id():
    with patch("core.device_identity.get_device_id") as mock:
        mock.return_value = "00000000-0000-0000-0000-000000000001"
        yield


@pytest.fixture
def in_memory_db():
    from core.storage import Storage

    storage = Storage(db_path=":memory:")
    yield storage
    storage.close()


@pytest.fixture
def mock_tick_bus():
    return MagicMock(spec=TickBus)


@pytest.fixture
def make_tick():
    _counter = 0

    def _make_tick(
        watcher: str = "foreground",
        data: dict | None = None,
        timestamp: datetime | None = None,
    ) -> Tick:
        nonlocal _counter
        _counter += 1
        return Tick(
            id=uuid.UUID(f"00000000-0000-0000-0000-{_counter:012d}"),
            watcher=watcher,
            timestamp=timestamp or datetime(2026, 7, 19, tzinfo=timezone.utc),
            data=data or {},
        )

    return _make_tick


class _MockWatcher:
    def __init__(self, config: WatcherConfig, tick_result: Tick | None):
        self.config = config
        self._tick_result = tick_result

    async def tick(self) -> Tick | None:
        return self._tick_result


@pytest.fixture
def mock_watcher():
    def _make(tick_result: Tick | None = None, **config_kwargs) -> _MockWatcher:
        return _MockWatcher(
            config=WatcherConfig(**config_kwargs),
            tick_result=tick_result,
        )

    return _make

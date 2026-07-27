import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class AppState:
    _instance: "AppState | None" = None

    def __new__(cls) -> "AppState":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._current_nav_index: int = 0
        self._collection_running: bool = False
        self._collection_paused: bool = False
        self._observers: dict[str, list[Callable[[], Any]]] = {}

    @property
    def current_nav_index(self) -> int:
        return self._current_nav_index

    @current_nav_index.setter
    def current_nav_index(self, value: int) -> None:
        self._current_nav_index = value
        self._notify("current_nav_index")

    @property
    def collection_running(self) -> bool:
        return self._collection_running

    @collection_running.setter
    def collection_running(self, value: bool) -> None:
        self._collection_running = value
        self._notify("collection_running")

    @property
    def collection_paused(self) -> bool:
        return self._collection_paused

    @collection_paused.setter
    def collection_paused(self, value: bool) -> None:
        self._collection_paused = value
        self._notify("collection_paused")

    def on_change(self, key: str, callback: Callable[[], Any]) -> None:
        self._observers.setdefault(key, []).append(callback)

    def _notify(self, key: str) -> None:
        for cb in self._observers.get(key, []):
            try:
                cb()
            except Exception:
                logger.exception("Observer error for %s", key)

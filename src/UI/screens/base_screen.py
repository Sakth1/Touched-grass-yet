from collections.abc import Callable
from typing import Any

import flet as ft

from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState


class BaseScreen(ft.Container):
    def __init__(self, state: AppState, **kwargs: Any) -> None:
        self.state = state
        self._dispose_fns: list[Callable[[], None]] = []
        super().__init__(expand=True, **kwargs)

    def build_content(self) -> ft.Control:
        raise NotImplementedError

    def on_enter(self) -> None:
        pass

    def on_exit(self) -> None:
        pass

    def on_resize(self, width_class: WindowWidthClass) -> None:
        pass

    def bind_state(self, key: str, callback: Callable[[], None]) -> None:
        dispose = self.state.subscribe(key, callback)
        self._dispose_fns.append(dispose)

    def dispose(self) -> None:
        for fn in self._dispose_fns:
            fn()
        self._dispose_fns.clear()






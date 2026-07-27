from datetime import date, timedelta
from typing import Any

import flet as ft

from ..theme.tokens import SPACING


class DateNavigator(ft.Row):
    def __init__(
        self,
        current_date: date | None = None,
        on_change: Any = None,
        **kwargs: Any,
    ) -> None:
        self._current = current_date or date.today()
        self._on_change = on_change

        self._label = ft.Text(
            self._current.strftime("%B %d, %Y"),
            size=16,
            weight=ft.FontWeight.W_600,
        )

        super().__init__(
            controls=[
                ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=self._prev, icon_size=20),
                self._label,
                ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=self._next, icon_size=20),
                ft.IconButton(icon=ft.Icons.CALENDAR_MONTH, on_click=self._pick, icon_size=20),
            ],
            spacing=SPACING["xs"],
            alignment=ft.MainAxisAlignment.CENTER,
            **kwargs,
        )

    def _prev(self, e: ft.ControlEvent) -> None:
        self._current -= timedelta(days=1)
        self._update()

    def _next(self, e: ft.ControlEvent) -> None:
        self._current += timedelta(days=1)
        self._update()

    def _pick(self, e: ft.ControlEvent) -> None:
        pass

    def _update(self) -> None:
        self._label.value = self._current.strftime("%B %d, %Y")
        self.update()
        if self._on_change:
            self._on_change(self._current)

    def set_date(self, d: date) -> None:
        self._current = d
        self._update()

    @property
    def current_date(self) -> date:
        return self._current






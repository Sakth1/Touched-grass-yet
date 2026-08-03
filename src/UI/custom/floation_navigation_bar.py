from __future__ import annotations

from dataclasses import field
from typing import Callable, Optional

import flet as ft


@ft.control
class FloatingNavigationBarDestination(ft.Container):
    """One pill: icon when unselected, label when selected (toggleable)."""

    icon: str = ft.Icons.HELP
    label: str = ""
    selected: bool = False
    on_select: Optional[Callable[["FloatingNavigationBarDestination"], None]] = None

    def init(self):
        self._icon = ft.Icon(icon=self.icon, color=self._color())
        self._text = ft.Text(self.label, color=self._color(), size=12)
        self.padding = ft.padding.Padding.only(top=8, bottom=8, left=8, right=8)
        self.border_radius = 20
        self.ink = True
        self.animate = 200
        self.on_click = self._handle_click
        self._render()

    def _color(self) -> str:
        return ft.Colors.WHITE if self.selected else ft.Colors.WHITE_54

    def _render(self) -> None:
        self.content = self._text if self.selected else self._icon
        self.bgcolor = ft.Colors.WHITE_10 if self.selected else None
        self._icon.color = self._color()
        self._text.color = self._color()

    def set_selected(self, value: bool) -> bool:
        if value == self.selected:
            return False
        self.selected = value
        self._render()
        return True

    def _handle_click(self, e) -> None:
        if self.on_select:
            self.on_select(self)


@ft.control
class FloatingNavigationBar(ft.Container):
    """Floating pill-style bottom navigation bar.

    Renders each destination as a :class:`FloatingNavigationBarDestination`
    inside a centered ``ft.Row``.
    """

    destinations: list[FloatingNavigationBarDestination] = field(default_factory=list, metadata={"skip": True})
    selected_index: int = 0
    label_behavior: Optional[ft.NavigationBarLabelBehavior] = None
    on_change: Optional[Callable[[ft.Event], None]] = None

    def init(self):
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        self.border_radius = 24
        self.margin = ft.margin.Margin(left=16, right=16, bottom=24)
        for i, dest in enumerate(self.destinations):
            dest.on_select = lambda d, i=i: self._select(i)
        self.content = ft.Row(
            controls=self.destinations,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            tight=True,
            run_spacing=0,
        )
        self._sync_selection()

    def before_update(self):
        self._sync_selection()

    def select_index(self, index: int) -> None:
        if index == self.selected_index:
            return
        self.selected_index = index
        changed = self._sync_selection()
        for dest in changed:
            if dest.parent is not None:
                dest.update()
        if self.on_change:
            self.on_change(ft.Event(name="FloatingNavigationChange", control=self))

    def _select(self, index: int) -> None:
        self.select_index(index)

    def _sync_selection(self) -> list[FloatingNavigationBarDestination]:
        changed: list[FloatingNavigationBarDestination] = []
        for i, dest in enumerate(self.destinations):
            if dest.set_selected(i == self.selected_index):
                changed.append(dest)
        return changed

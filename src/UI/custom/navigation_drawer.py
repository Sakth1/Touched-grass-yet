from __future__ import annotations

from dataclasses import field
from typing import Callable, Optional

import flet as ft

from utils.constants import MIN_EXTENDED_DRAWER_WIDTH, MIN_UNEXTENDED_DRAWER_WIDTH


@ft.control
class CustomNavigationDrawerDestination(ft.Container):
    icon: str = ft.Icons.HELP
    label: str = ""
    selected: bool = False
    on_select: Optional[Callable[["CustomNavigationDrawerDestination"], None]] = None

    def init(self):
        self._icon = ft.Icon(icon=self.icon, color=self._color())
        self._text = ft.Text(self.label, color=self._color(), size=12)
        self._display_label = True
        self.content_controls = (
            [self._icon, self._text] if self._display_label else [self._icon]
        )
        self.content = ft.Row(
            controls=self.content_controls,
            spacing=10,
        )
        self.border_radius = 20
        self.ink = True
        self.animate = 200
        self.on_click = self._handle_click
        self._render()

    def _render(self) -> None:
        self.content.controls = (
            [self._icon, self._text] if self._display_label else [self._icon]
        )
        self.bgcolor = ft.Colors.WHITE_10 if self.selected else None
        self._icon.color = self._color()
        self._text.color = self._color()
        if self.parent is not None:
            self.update()

    def _color(self) -> str:
        return ft.Colors.WHITE if self.selected else ft.Colors.WHITE_54

    def _handle_click(self, e):
        if self.on_select:
            self.on_select(self)

    def toggle_label(self):
        self._display_label = not self._display_label
        self._render()

    def set_selected(self, value: bool) -> bool:
        if value == self.selected:
            return False
        self.selected = value
        self._render()
        return True


@ft.control
class CustomNavigationDrawer(ft.Container):
    destinations: list[CustomNavigationDrawerDestination] = field(
        default_factory=list, metadata={"skip": True}
    )
    include_hamburger: bool = True
    extended: bool = True
    trailing: Optional[CustomNavigationDrawerDestination] = field(
        default=None, metadata={"skip": True}
    )
    selected_index: int = 0
    on_change: Optional[Callable[[ft.Event], None]] = None

    def init(self):
        self.bgcolor = ft.Colors.SURFACE_CONTAINER

        for i, dest in enumerate(self.destinations):
            dest.on_select = lambda d, i=i: self._select(i)

        if self.trailing is not None:
            self.trailing.on_select = lambda d: self._select(len(self.destinations))

        self.final_destinations: list[CustomNavigationDrawerDestination] = [
            i for i in self.destinations if i is not None
        ]
        self.hamburger_button = ft.IconButton(
            icon=ft.icons.Icons.MENU if self.extended else ft.icons.Icons.MENU,
            tooltip="Collapse" if self.extended else "Expand",
            on_click=self._toggle_drawer,
            visible=self.include_hamburger,
            margin=ft.margin.Margin.only(left=10),
            padding=ft.padding.Padding.only(left=8, right=8),
        )

        self.drawer_content = [
            i
            for i in [
                self.hamburger_button,
                *self.final_destinations,
                ft.Container(expand=True),
                self.trailing,
            ]
            if i is not None
        ]

        self.content = ft.Column(
            controls=self.drawer_content,
            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
            tight=True,
            expand=True,
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

    def _sync_selection(self) -> list[CustomNavigationDrawerDestination]:
        changed: list[CustomNavigationDrawerDestination] = []
        for i, dest in enumerate(self.destinations):
            if dest.set_selected(i == self.selected_index):
                changed.append(dest)
        return changed

    def _toggle_drawer(self):
        if self.extended is True:
            self.width = MIN_UNEXTENDED_DRAWER_WIDTH
        else:
            self.width = MIN_EXTENDED_DRAWER_WIDTH
        for dest in self.final_destinations:
            dest.toggle_label()
        if self.trailing is not None:
            self.trailing.toggle_label()
        self.extended = not self.extended

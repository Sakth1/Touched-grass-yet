from __future__ import annotations

from dataclasses import field
from typing import Callable, Optional

import flet as ft

from UI.layout.metrics import DrawerMetrics, resolve_drawer_metrics
from utils.constants import EXTENDED_RAIL_MIN_WIDTH, MINI_RAIL_WIDTH
from utils.models import AppLayout, NavigationPattern


@ft.control
class CustomNavigationDrawerDestination(ft.Container):
    icon: str = ft.Icons.HELP
    label: str = ""
    selected: bool = False
    on_select: Optional[Callable[["CustomNavigationDrawerDestination"], None]] = None

    def init(self):
        self._icon = ft.Icon(icon=self.icon, color=self._color())
        self._text = ft.Text(self.label, color=self._color(), size=12)
        self.padding = ft.padding.Padding.only(top=4, bottom=4, left=8, right=8)
        self._display_label = True
        self.content_controls: list[ft.Control] = (
            [self._icon, self._text] if self._display_label else [self._icon]
        )
        self.content: Optional[ft.Control] = ft.Row(controls=self.content_controls)
        self.border_radius = 10
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

    def apply_metrics(self, metrics: DrawerMetrics) -> None:
        self.padding = ft.padding.Padding.only(
            top=4,
            bottom=4,
            left=metrics.destination_padding,
            right=metrics.destination_padding,
        )
        if self.content is not None:
            if self._display_label:
                self.content.alignment = ft.MainAxisAlignment.START
                self.content.spacing = metrics.item_spacing
            else:
                self.content.alignment = ft.MainAxisAlignment.CENTER
                self.content.spacing = 0
        if self.parent is not None:
            self.update()


@ft.control
class CustomNavigationDrawer(ft.Container):
    destinations: list[CustomNavigationDrawerDestination] = field(
        default_factory=list, metadata={"skip": True}
    )
    extended: bool = True
    layout: Optional[AppLayout] = field(default=None, metadata={"skip": True})
    trailing: CustomNavigationDrawerDestination = field(
        default_factory=list, metadata={"skip": True}
    )
    selected_index: int = 0
    on_change: Optional[Callable[[ft.Event], None]] = None

    def init(self):
        self._layout: Optional[AppLayout] = None
        self.bgcolor = ft.Colors.SURFACE_CONTAINER
        for i, dest in enumerate(self.destinations):
            dest.on_select = lambda d, i=i: self._select(i)

        if self.trailing is not None:
            self.trailing.on_select = lambda d: self._select(len(self.destinations))

        self.final_destinations: list[CustomNavigationDrawerDestination] = [
            i for i in self.destinations if i is not None
        ]

        self.all_destinations: list[CustomNavigationDrawerDestination] = [*self.final_destinations, self.trailing]

        self.drawer_content = [
            i
            for i in [
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

        self._apply_metrics()
        self._select(self.selected_index, app_init=True)

    def before_update(self):
        self._sync_selection()

    def select_index(self, index: int, app_init: bool = False) -> None:
        if index == self.selected_index and not app_init:
            return
        self.selected_index = index
        changed = self._sync_selection()
        for dest in changed:
            if dest.parent is not None:
                dest.update()
        if self.on_change:
            self.on_change(ft.Event(name="FloatingNavigationChange", control=self))

    def _select(self, index: int, app_init: bool = False) -> None:
        self.select_index(index, app_init)

    def _sync_selection(self) -> list[CustomNavigationDrawerDestination]:
        changed: list[CustomNavigationDrawerDestination] = []
        for i, dest in enumerate(self.all_destinations):
            if dest.set_selected(i == self.selected_index):
                changed.append(dest)
        return changed

    def apply_layout(self, layout: AppLayout) -> None:
        """Re-derive width, padding, spacing, and label mode from a layout."""
        self._layout = layout
        if layout.navigation is NavigationPattern.MINI_RAIL:
            self._apply_extended(False)
        else:
            self._apply_extended(True)
        self._apply_metrics()

    def _apply_extended(self, extended: bool) -> None:
        if extended == self.extended:
            return
        self.extended = extended
        for dest in self.all_destinations:
            dest.toggle_label()
        if self.trailing is not None:
            self.trailing.toggle_label()

    def _current_metrics(self) -> DrawerMetrics:
        if self.extended and self._layout is not None:
            return resolve_drawer_metrics(self._layout)
        if self.extended:
            return DrawerMetrics(
                width=float(EXTENDED_RAIL_MIN_WIDTH),
                destination_padding=12.0,
                item_spacing=8.0,
            )
        return DrawerMetrics(
            width=float(MINI_RAIL_WIDTH),
            destination_padding=8.0,
            item_spacing=4.0,
        )

    def _apply_metrics(self) -> None:
        metrics = self._current_metrics()
        self.width = metrics.width
        self.content.run_spacing = metrics.item_spacing
        for dest in self.all_destinations:
            dest.apply_metrics(metrics)
        if self.trailing is not None:
            self.trailing.apply_metrics(metrics)

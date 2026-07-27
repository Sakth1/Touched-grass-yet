import logging
from typing import Callable

import flet as ft

from UI.layouts.responsive_scaffold import ROUTE_TO_INDEX, ResponsiveScaffold
from UI.state.app_state import AppState

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, page: ft.Page, state: AppState, scaffold: ResponsiveScaffold) -> None:
        self.page = page
        self.state = state
        self.scaffold = scaffold
        self._routes: dict[str, Callable[[], ft.Control]] = {}

        page.on_route_change = self._on_route_change

    def register(self, route: str, builder: Callable[[], ft.Control]) -> None:
        self._routes[route] = builder

    def navigate(self, route: str) -> None:
        if route in self._routes:
            self.page.go(route)

    def _on_route_change(self, e: ft.RouteChangeEvent) -> None:
        route = e.route
        if route in self._routes:
            self.state.current_nav_index = ROUTE_TO_INDEX.get(route, 0)
            content = self._routes[route]()
            self.scaffold.set_content(content)
        else:
            self.navigate("/")

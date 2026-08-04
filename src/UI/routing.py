from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from UI.custom.navigation_bar import CustomNavigationBar

logger = logging.getLogger(__name__)


class RouteManager:
    def __init__(
        self,
        page: ft.Page,
        container: ft.Container,
        route_views: dict[str, object],
        route_to_index: dict[str, int] | None = None,
    ):
        self._page: ft.Page = page
        self._container: ft.Container = container
        self._route_views: dict[str, object] = route_views
        self._route_to_index: dict[str, int] | None = route_to_index

    def navigate(self, route: str) -> None:
        try:
            new_view = self._route_views.get(route)
            if new_view is None:
                logger.warning("Unknown route=%s, falling back to /home", route)
                route = "/home"
                new_view = self._route_views.get("/home")

            self._container.content = new_view
            self.current_route = route

            idx = self._route_to_index.get(route, 0)
            nav: CustomNavigationBar | None = getattr(
                self._page, "navigation_bar", None
            )
            if nav is not None:
                nav.select_index(idx)

            navigate = getattr(self._page, "navigate", None)
            if callable(navigate):
                navigate(route)
                return
            self._page.run_task(self._push_route, route)

        except Exception:
            logger.exception("Route transition failed route=%s", route)

    async def _push_route(self, route: str) -> None:
        """Navigate from synchronous callbacks without leaking a coroutine."""
        await self._page.push_route(route)

    def handle_route_change(self, event) -> None:
        """Handle ``page.on_route_change`` and navigate accordingly.

        If the route is already current (e.g. already set by
        :meth:`swap_view` in the async flow), the event is
        silently ignored to prevent duplicate lifecycle calls.
        """
        route = getattr(event, "route", None) or "/dashboard"
        if route == self.current_route:
            return
        self.navigate(route)

    def handle_navigation_change(self, event: ft.Event[CustomNavigationBar]) -> None:
        """Handle ``page.navigation_bar.on_change`` and navigate accordingly."""
        idx = getattr(event.control, "selected_index", None)
        route_by_index = {v: k for k, v in self._route_to_index.items()}
        route = route_by_index.get(idx or 0, "/dashboard")
        self.navigate(route)

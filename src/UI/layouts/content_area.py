import flet as ft

from ..screens.base_screen import BaseScreen
from ..services.state import AppState, Destination

_SCREEN_LABELS: dict[Destination, str] = {
    Destination.DASHBOARD: "Dashboard",
    Destination.TIMELINE: "Timeline",
    Destination.ANALYTICS: "Analytics",
    Destination.SETTINGS: "Settings",
}


class ContentArea(ft.Container):
    def __init__(self, state: AppState) -> None:
        self.state = state
        self._screens: dict[Destination, BaseScreen] = {}
        self._switcher = ft.AnimatedSwitcher(
            content=ft.Container(),
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=250,
            reverse_duration=250,
            switch_in_curve=ft.AnimationCurve.EASE_OUT,
            switch_out_curve=ft.AnimationCurve.EASE_IN,
        )

        super().__init__(
            expand=True,
            content=self._switcher,
        )

    def register_screen(self, destination: Destination, screen: BaseScreen) -> None:
        self._screens[destination] = screen

    def navigate_to(self, destination: Destination) -> None:
        current = self._switcher.content
        if isinstance(current, BaseScreen):
            current.on_exit()

        screen = self._screens.get(destination)
        if screen:
            screen.on_enter()
            self._switcher.content = screen

    def get_current_screen(self) -> BaseScreen | None:
        content = self._switcher.content
        if isinstance(content, BaseScreen):
            return content
        return None






import flet as ft

from ..core.breakpoints import WindowWidthClass
from ..services.state import AppState
from ..theme.tokens import SPACING


class ContextPanel(ft.Container):
    def __init__(self, state: AppState, width_class: WindowWidthClass) -> None:
        self.state = state
        self.width_class = width_class

        self._title = ft.Text("", size=16, weight=ft.FontWeight.W_600)
        self._body = ft.Column(spacing=SPACING["sm"], scroll=ft.ScrollMode.AUTO)

        content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            self._title,
                            ft.IconButton(
                                icon=ft.Icons.CLOSE,
                                icon_size=18,
                                on_click=lambda _: self._close(),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.Padding.only(
                        left=SPACING["md"], right=SPACING["xs"], top=SPACING["sm"]
                    ),
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=self._body,
                    padding=ft.padding.Padding.all(SPACING["md"]),
                    expand=True,
                ),
            ],
            spacing=0,
        )

        super().__init__(
            width=self._panel_width(),
            animate=ft.Animation(200, ft.AnimationCurve.EASE_OUT),
            bgcolor=ft.Colors.SURFACE_CONTAINER if self._should_show() else None,
            padding=ft.padding.Padding.only(left=1),
            content=content if self._should_show() else None,
        )

    def _should_show(self) -> bool:
        return self.state.context_open and self.width_class != WindowWidthClass.COMPACT

    def _panel_width(self) -> int:
        return 280 if self._should_show() else 0

    def _close(self) -> None:
        self.state.context_open = False

    def set_content(self, title: str, controls: list[ft.Control]) -> None:
        self._title.value = title
        self._body.controls = controls
        self.state.context_content = {"title": title, "controls": controls}
        self.state.context_open = True

    def sync(self) -> None:
        show = self._should_show()
        self.width = self._panel_width()
        self.bgcolor = ft.Colors.SURFACE_CONTAINER if show else None
        if not show:
            self.content = None
        else:
            self._rebuild_content()
        self.update()

    def _rebuild_content(self) -> None:
        cc = self.state.context_content
        if cc:
            self._title.value = cc.get("title", "")
            self._body.controls = cc.get("controls", [])
        self.content = ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            self._title,
                            ft.IconButton(icon=ft.Icons.CLOSE, icon_size=18, on_click=lambda _: self._close()),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=ft.padding.Padding.only(left=SPACING["md"], right=SPACING["xs"], top=SPACING["sm"]),
                ),
                ft.Divider(height=1),
                ft.Container(content=self._body, padding=ft.padding.Padding.all(SPACING["md"]), expand=True),
            ],
            spacing=0,
        )

    def update_width_class(self, width_class: WindowWidthClass) -> None:
        self.width_class = width_class
        self.sync()

    def get_bottom_sheet_content(self) -> ft.Control | None:
        if self.state.context_content:
            cc = self.state.context_content
            return ft.Column(
                controls=[
                    ft.Text(cc.get("title", ""), size=16, weight=ft.FontWeight.W_600),
                    ft.Divider(height=1),
                    ft.Column(controls=cc.get("controls", []), spacing=SPACING["sm"]),
                ],
                spacing=SPACING["sm"],
            )
        return None






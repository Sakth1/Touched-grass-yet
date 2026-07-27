import flet as ft


class FilterChips(ft.Row):
    def __init__(
        self,
        options: list[tuple[str, str]],
        selected: set[str] | None = None,
        on_change: ft.ControlEventHandler | None = None,
    ) -> None:
        self._chips: list[ft.Chip] = []
        chips: list[ft.Chip] = []
        for value, label in options:
            chip = ft.Chip(
                label=ft.Text(label),
                selected=value in (selected or set()),
                on_select=on_change,
                data=value,
            )
            chips.append(chip)
        self._chips = chips
        super().__init__(controls=chips, spacing=8, wrap=True)

    @property
    def selected_values(self) -> list[str]:
        return [c.data for c in self._chips if c.selected]






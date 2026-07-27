import flet as ft

from .tokens import DEFAULT_SEED, SEED_COLORS


def build_theme(seed_color_name: str = DEFAULT_SEED, dark: bool = True) -> ft.Theme:
    seed = SEED_COLORS.get(seed_color_name, SEED_COLORS[DEFAULT_SEED])
    theme = ft.Theme(
        use_material3=True,
        color_scheme_seed=seed,
        font_family="Segoe UI",
    )

    theme.page_transitions_android = ft.PageTransitionTheme.FADE_UPWARDS
    theme.page_transitions_ios = ft.PageTransitionTheme.FADE_UPWARDS
    theme.page_transitions_macos = ft.PageTransitionTheme.FADE_UPWARDS
    theme.page_transitions_linux = ft.PageTransitionTheme.FADE_UPWARDS
    theme.page_transitions_windows = ft.PageTransitionTheme.FADE_UPWARDS

    theme.card_theme = ft.CardTheme(
        elevation=1,
        shape=ft.RoundedRectangleBorder(radius=12),
    )

    theme.navigation_bar_theme = ft.NavigationBarTheme(
        elevation=3,
        indicator_shape=ft.RoundedRectangleBorder(radius=8),
    )

    theme.navigation_rail_theme = ft.NavigationRailTheme(
        elevation=0,
        indicator_shape=ft.RoundedRectangleBorder(radius=8),
        label_type=ft.NavigationRailLabelType.ALL,
    )

    theme.bottom_app_bar_theme = ft.BottomAppBarTheme(elevation=3)

    if dark:
        theme.page_transitions_dark_android = ft.PageTransitionTheme.FADE_UPWARDS
        theme.page_transitions_dark_ios = ft.PageTransitionTheme.FADE_UPWARDS
        theme.page_transitions_dark_macos = ft.PageTransitionTheme.FADE_UPWARDS
        theme.page_transitions_dark_linux = ft.PageTransitionTheme.FADE_UPWARDS
        theme.page_transitions_dark_windows = ft.PageTransitionTheme.FADE_UPWARDS

    return theme






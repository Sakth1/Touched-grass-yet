import flet as ft

from UI.theme.tokens import SEED_COLOR


def build_text_theme() -> ft.TextTheme:
    return ft.TextTheme(
        display_large=ft.TextStyle(size=57, weight=ft.FontWeight.W_700),
        display_medium=ft.TextStyle(size=45, weight=ft.FontWeight.W_700),
        display_small=ft.TextStyle(size=36, weight=ft.FontWeight.W_700),
        headline_large=ft.TextStyle(size=32, weight=ft.FontWeight.W_600),
        headline_medium=ft.TextStyle(size=28, weight=ft.FontWeight.W_600),
        headline_small=ft.TextStyle(size=24, weight=ft.FontWeight.W_600),
        title_large=ft.TextStyle(size=22, weight=ft.FontWeight.W_500),
        title_medium=ft.TextStyle(size=16, weight=ft.FontWeight.W_500),
        title_small=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
        body_large=ft.TextStyle(size=16, weight=ft.FontWeight.W_400),
        body_medium=ft.TextStyle(size=14, weight=ft.FontWeight.W_400),
        body_small=ft.TextStyle(size=12, weight=ft.FontWeight.W_400),
        label_large=ft.TextStyle(size=14, weight=ft.FontWeight.W_500),
        label_medium=ft.TextStyle(size=12, weight=ft.FontWeight.W_500),
        label_small=ft.TextStyle(size=11, weight=ft.FontWeight.W_500),
    )


def build_card_theme() -> ft.CardTheme:
    return ft.CardTheme(
        elevation=1,
        shape=ft.RoundedRectangleBorder(radius=12),
        margin=4,
    )


def build_navigation_bar_theme() -> ft.NavigationBarTheme:
    return ft.NavigationBarTheme(
        elevation=3,
        label_behavior=ft.NavigationBarLabelBehavior.ONLY_SHOW_SELECTED,
    )


def build_navigation_rail_theme() -> ft.NavigationRailTheme:
    return ft.NavigationRailTheme(
        elevation=3,
        label_type=ft.NavigationRailLabelType.ALL,
    )


def build_page_transitions_theme() -> ft.PageTransitionsTheme:
    return ft.PageTransitionsTheme(
        android=ft.PageTransitionTheme.ZOOM,
        ios=ft.PageTransitionTheme.ZOOM,
        windows=ft.PageTransitionTheme.ZOOM,
        linux=ft.PageTransitionTheme.ZOOM,
        macos=ft.PageTransitionTheme.ZOOM,
    )


def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=SEED_COLOR,
        use_material3=True,
        text_theme=build_text_theme(),
        card_theme=build_card_theme(),
        navigation_bar_theme=build_navigation_bar_theme(),
        navigation_rail_theme=build_navigation_rail_theme(),
        page_transitions=build_page_transitions_theme(),
    )


def build_dark_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=SEED_COLOR,
        use_material3=True,
        text_theme=build_text_theme(),
        card_theme=build_card_theme(),
        navigation_bar_theme=build_navigation_bar_theme(),
        navigation_rail_theme=build_navigation_rail_theme(),
        page_transitions=build_page_transitions_theme(),
    )

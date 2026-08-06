"""Tests for the layout-driven metrics of the custom navigation controls.

The resolver functions in :mod:`UI.layout.metrics` are pure — an
:class:`AppLayout` in, frozen metric dataclasses out — so the drawer and
floating bar behaviour on every window size is pinned here without needing a
live Flet client.
"""

from __future__ import annotations

from utils.layout import app_layout_resolver
from utils.models import NavigationPattern


class TestDrawerMetrics:
    def test_mini_rail_width_fixed(self):
        layout = app_layout_resolver(800, 1280)
        from UI.layout.metrics import resolve_drawer_metrics

        metrics = resolve_drawer_metrics(layout)
        assert layout.navigation is NavigationPattern.MINI_RAIL
        assert metrics.width == 60

    def test_tablet_landscape_extended_width_scales_with_viewport(self):
        from UI.layout.metrics import resolve_drawer_metrics

        layout = app_layout_resolver(960, 600)
        metrics = resolve_drawer_metrics(layout)
        assert 200 <= metrics.width <= 300
        assert metrics.width == 960 * 0.22

    def test_desktop_extended_width_capped_at_max(self):
        from UI.layout.metrics import resolve_drawer_metrics

        layout = app_layout_resolver(3000, 1600)
        metrics = resolve_drawer_metrics(layout)
        assert metrics.width == 300

    def test_extended_uses_roomier_padding_on_wide_layouts(self):
        from UI.layout.metrics import resolve_drawer_metrics

        landscape = resolve_drawer_metrics(app_layout_resolver(960, 600))
        desktop = resolve_drawer_metrics(app_layout_resolver(1280, 800))
        assert landscape.destination_padding == 12
        assert desktop.destination_padding == 12
        assert landscape.item_spacing == 8
        assert desktop.item_spacing == 8


class TestNavBarMetrics:
    def test_phone_portrait_margins(self):
        from UI.layout.metrics import resolve_navbar_metrics

        metrics = resolve_navbar_metrics(app_layout_resolver(400, 800))
        assert metrics.margin_left == 16
        assert metrics.margin_right == 16
        assert metrics.margin_bottom == 24
        assert metrics.destination_padding == 8

    def test_phone_landscape_sits_lower_and_roomier(self):
        from UI.layout.metrics import resolve_navbar_metrics

        metrics = resolve_navbar_metrics(app_layout_resolver(700, 400))
        assert metrics.margin_left == 24
        assert metrics.margin_bottom == 16  # compact height → lower to the floor
        assert metrics.destination_padding == 10

    def test_bottom_margin_clears_gesture_inset(self):
        from UI.layout.metrics import resolve_navbar_metrics

        layout = app_layout_resolver(
            400,
            800,
            media=__import__("types").SimpleNamespace(
                orientation=None,
                padding=__import__("types").SimpleNamespace(
                    left=0, top=0, right=0, bottom=34
                ),
            ),
        )
        metrics = resolve_navbar_metrics(layout)
        assert metrics.margin_bottom == 24 + 34

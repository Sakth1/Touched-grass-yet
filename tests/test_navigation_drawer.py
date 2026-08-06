from UI.custom.navigation_drawer import (
    CustomNavigationDrawer,
    CustomNavigationDrawerDestination,
)


class TestDestinationConstruction:
    def test_constructs_without_page(self):
        dest = CustomNavigationDrawerDestination(
            icon="HOME", label="Dashboard", selected=True
        )
        assert len(dest.content.controls) == 2
        assert dest.bgcolor is not None

    def test_toggle_label_swaps_row_controls(self):
        dest = CustomNavigationDrawerDestination(icon="HOME", label="Dashboard")
        assert len(dest.content.controls) == 2

        dest.toggle_label()
        assert len(dest.content.controls) == 1

        dest.toggle_label()
        assert len(dest.content.controls) == 2

    def test_set_selected_renders_without_crashing(self):
        dest = CustomNavigationDrawerDestination(icon="HOME", label="Dashboard")
        assert dest.set_selected(True) is True
        assert dest.selected is True
        assert dest.set_selected(True) is False


class TestDrawerConstruction:
    def test_constructs_with_destinations_and_trailing(self):
        dest = CustomNavigationDrawerDestination(icon="HOME", label="Dashboard")
        trailing = CustomNavigationDrawerDestination(icon="SETTINGS", label="Settings")
        CustomNavigationDrawer(
            destinations=[dest],
            trailing=trailing,
            selected_index=0,
        )
        assert dest.selected is True
        assert trailing.selected is False

    def test_select_index_updates_selection(self):
        first = CustomNavigationDrawerDestination(icon="HOME", label="Dashboard")
        second = CustomNavigationDrawerDestination(icon="TIMELINE", label="Timeline")
        drawer = CustomNavigationDrawer(
            destinations=[first, second],
            selected_index=0,
        )
        drawer.select_index(1)
        assert first.selected is False
        assert second.selected is True


class TestDrawerResponsiveLayout:
    @staticmethod
    def _drawer(extended=True):
        return CustomNavigationDrawer(
            destinations=[
                CustomNavigationDrawerDestination(icon="HOME", label="Dashboard"),
                CustomNavigationDrawerDestination(icon="TIMELINE", label="Timeline"),
            ],
            trailing=CustomNavigationDrawerDestination(
                icon="SETTINGS", label="Settings"
            ),
            extended=extended,
        )

    def test_mini_rail_collapses_labels(self):
        from utils.layout import app_layout_resolver

        drawer = self._drawer(extended=True)
        layout = app_layout_resolver(800, 1280)  # tablet portrait -> mini rail

        drawer.apply_layout(layout)

        assert drawer.extended is False
        assert drawer.width == 60
        assert len(drawer.final_destinations[0].content.controls) == 1  # icon only

    def test_expanded_rail_shows_labels(self):
        from utils.layout import app_layout_resolver

        drawer = self._drawer(extended=True)
        layout = app_layout_resolver(1280, 800)  # desktop -> extended rail

        drawer.apply_layout(layout)

        assert drawer.extended is True
        assert len(drawer.final_destinations[0].content.controls) == 2  # icon + label
        assert 120 <= drawer.width <= 200

    def test_layout_always_wins_over_initial_state(self):
        from utils.layout import app_layout_resolver

        drawer = self._drawer(extended=True)
        drawer.apply_layout(app_layout_resolver(800, 1280))
        assert drawer.extended is False

        drawer.apply_layout(app_layout_resolver(1280, 800))
        assert drawer.extended is True

        # a collapsed-created drawer is forced extended by a wide layout
        drawer = self._drawer(extended=False)
        drawer.apply_layout(app_layout_resolver(960, 600))
        assert drawer.extended is True

    def test_reapplying_same_layout_is_idempotent(self):
        from utils.layout import app_layout_resolver

        drawer = self._drawer(extended=True)
        layout = app_layout_resolver(1280, 800)

        drawer.apply_layout(layout)
        first = [len(d.content.controls) for d in drawer.final_destinations]

        drawer.apply_layout(layout)
        assert [len(d.content.controls) for d in drawer.final_destinations] == first
        assert drawer.extended is True

    def test_width_scales_with_viewport(self):
        from utils.layout import app_layout_resolver

        drawer = self._drawer(extended=True)
        layout = app_layout_resolver(900, 600)
        drawer.apply_layout(layout)
        assert drawer.width == 900 * 0.22

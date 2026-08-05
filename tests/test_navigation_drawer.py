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

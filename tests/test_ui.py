import logging
from unittest.mock import MagicMock, patch

import flet as ft
import pytest


class TestFletTextFieldContract:
    def test_text_field_with_text_style_succeeds(self):
        field = ft.TextField(
            value="test",
            multiline=True,
            read_only=True,
            text_style=ft.TextStyle(size=11, font_family="monospace"),
            bgcolor=ft.Colors.TRANSPARENT,
            border=ft.InputBorder.NONE,
        )
        assert isinstance(field, ft.TextField)
        assert field.value == "test"

    def test_text_field_rejects_font_family_directly(self):
        with pytest.raises(TypeError, match="font_family"):
            ft.TextField(
                value="test",
                multiline=True,
                read_only=True,
                font_family="monospace",
            )

    def test_text_accepts_font_family_directly(self):
        t = ft.Text("hello", size=11, font_family="monospace")
        assert isinstance(t, ft.Text)
        assert t.font_family == "monospace"


class TestSettingsPanelErrorHandling:
    @pytest.fixture
    def mock_page(self):
        page = MagicMock(spec=ft.Page)
        page.set_clipboard = MagicMock()
        return page

    @pytest.fixture
    def panel(self, mock_page):
        from UI.settings_page import SettingsPanel

        return SettingsPanel(mock_page, MagicMock())

    def test_load_log_handles_empty_log(self, panel):
        with patch("UI.settings_page.read_log_lines", return_value=[]):
            panel._load_log()
        assert len(panel._log_scroll.controls) >= 1
        text = panel._log_scroll.controls[0]
        assert isinstance(text, ft.Text)
        assert "No log file found" in text.value

    def test_load_log_handles_normal_log(self, panel):
        lines = ["line1\n", "line2\n"]
        with patch("UI.settings_page.read_log_lines", return_value=lines):
            panel._load_log()
        assert len(panel._log_scroll.controls) >= 1
        field = panel._log_scroll.controls[0]
        assert isinstance(field, ft.TextField)
        assert field.value == "line1\nline2"

    def test_load_log_error_boundary_catches_exceptions(self, panel, caplog):
        with (
            patch("UI.settings_page.read_log_lines", side_effect=RuntimeError("boom")),
            caplog.at_level(logging.ERROR),
        ):
            panel._load_log()
        assert "Failed to load log" in caplog.text
        assert any("Error loading log" in c.value for c in panel._log_scroll.controls if isinstance(c, ft.Text))
        assert panel._status_text.value == "Failed to load log"

    def test_load_log_despite_corrupt_log_data(self, panel):
        with patch("UI.settings_page.read_log_lines", return_value=[None, 42]):
            panel._load_log()
        assert len(panel._log_scroll.controls) >= 1

    def test_copy_log_handles_empty(self, panel):
        with patch("UI.settings_page.read_log_lines", return_value=[]):
            panel._copy_log()
        assert panel._status_text.value != "Copied to clipboard"

    def test_copy_log_copies_content(self, panel):
        with (
            patch("UI.settings_page.read_log_lines", return_value=["hello\n"]),
            patch("UI.settings_page.ft.Clipboard") as mock_cls,
        ):
            mock_cls().set = MagicMock()
            panel._copy_log()
            mock_cls().set.assert_called_once_with("hello\n")
        assert panel._status_text.value == "Copied to clipboard"

    def test_copy_log_handles_clipboard_error(self, panel):
        with (
            patch("UI.settings_page.read_log_lines", return_value=["data\n"]),
            patch("UI.settings_page.ft.Clipboard") as mock_cls,
        ):
            mock_cls().set = MagicMock(side_effect=RuntimeError("clipboard fail"))
            panel._copy_log()
        assert panel._status_text.value == "Failed to copy"

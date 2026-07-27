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




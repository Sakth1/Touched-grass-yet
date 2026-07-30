import flet as ft
import pytest


class _FakeWindow:
    width = None
    height = None


class _FakePage:
    def __init__(self):
        self.window = _FakeWindow()
        self.title = None
        self.theme_mode = None
        self.updated = False

    def update(self):
        self.updated = True


@pytest.mark.asyncio
async def test_app_entrypoint_awaits_startup_without_nested_event_loop(monkeypatch):
    import app
    from utils.models import SystemType

    class FakeCollectionManager:
        def __init__(self):
            self.config = type("Config", (), {"auto_start_enabled": False})()

        def detect_platform(self):
            return SystemType.WINDOWS

    monkeypatch.setattr(app, "setup_file_logging", lambda: None)
    monkeypatch.setattr(app, "CollectionManager", FakeCollectionManager)
    monkeypatch.setattr(app, "Dashboard", lambda: object())

    page = _FakePage()

    await app.entrypoint(page)

    assert page.updated is True


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




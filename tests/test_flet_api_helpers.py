"""Unit tests for the flet API compatibility test's helper functions."""

from __future__ import annotations

import ast
import inspect
import sys
from pathlib import Path

import flet as ft

# Allow importing from the test package itself
sys.path.insert(0, str(Path(__file__).parent))

from test_flet_api_compat import (
    SRC_DIR,
    _get_flet_imports,
    _has_flet_imports,
    _has_var_keyword,
    _mro_annotations,
    _mro_dataclass_fields,
    _rel,
    _resolve_attr_chain,
    _resolve_ft_chain,
    _resolve_signature,
    _resolve_typed_target,
    _to_ft_chain,
)

# ===========================================================================
# _resolve_attr_chain
# ===========================================================================


class TestResolveAttrChain:
    def test_simple_name(self):
        node = ast.Name(id="ft")
        assert _resolve_attr_chain(node) == ["ft"]

    def test_two_part(self):
        node = ast.Attribute(value=ast.Name(id="ft"), attr="Page")
        assert _resolve_attr_chain(node) == ["ft", "Page"]

    def test_three_part(self):
        node = ast.Attribute(
            value=ast.Attribute(value=ast.Name(id="ft"), attr="Colors"),
            attr="RED",
        )
        assert _resolve_attr_chain(node) == ["ft", "Colors", "RED"]

    def test_non_attr_returns_none(self):
        node = ast.Constant(value=42)
        assert _resolve_attr_chain(node) is None

    def test_call_returns_none(self):
        node = ast.Call(func=ast.Name(id="ft"), args=[], keywords=[])
        assert _resolve_attr_chain(node) is None


# ===========================================================================
# _to_ft_chain
# ===========================================================================


class TestToFtChain:
    _DIRECT = {"ft": "flet", "ctrl": "flet.controls"}
    _PREFIXED = {"Foo": "flet.Foo", "Bar": "flet.controls.Bar"}

    def test_direct_import_simple(self):
        assert _to_ft_chain(["ft", "Page"], self._DIRECT, {}) == ("Page",)

    def test_direct_import_nested(self):
        assert _to_ft_chain(["ft", "Colors", "RED"], self._DIRECT, {}) == ("Colors", "RED")

    def test_direct_submodule(self):
        assert _to_ft_chain(["ctrl", "X"], self._DIRECT, {}) == ("controls", "X")

    def test_prefixed_import(self):
        assert _to_ft_chain(["Foo", "Y"], {}, self._PREFIXED) == ("Foo", "Y")

    def test_prefixed_submodule(self):
        assert _to_ft_chain(["Bar", "Z"], {}, self._PREFIXED) == ("controls", "Bar", "Z")

    def test_unknown_root_returns_none(self):
        assert _to_ft_chain(["unknown", "X"], self._DIRECT, {}) is None

    def test_non_flet_direct_returns_none(self):
        dirs_only = {"other": "other_lib"}
        assert _to_ft_chain(["other", "X"], dirs_only, {}) is None


# ===========================================================================
# _has_flet_imports
# ===========================================================================


class TestHasFletImports:
    def test_true_with_direct(self):
        assert _has_flet_imports({"ft": "flet"}, {}) is True

    def test_true_with_prefixed(self):
        assert _has_flet_imports({}, {"Foo": "flet.Foo"}) is True

    def test_false_empty(self):
        assert _has_flet_imports({}, {}) is False


# ===========================================================================
# _resolve_ft_chain
# ===========================================================================


class TestResolveFtChain:
    def test_resolve_top_level(self):
        obj, missing, idx = _resolve_ft_chain(("Page",))
        assert missing is None
        assert obj is ft.Page

    def test_resolve_nested(self):
        obj, missing, idx = _resolve_ft_chain(("Colors", "RED"))
        assert missing is None

    def test_missing_top_level(self):
        obj, missing, idx = _resolve_ft_chain(("NonExistent12345",))
        assert obj is None
        assert missing == "NonExistent12345"
        assert idx == 0

    def test_missing_nested(self):
        obj, missing, idx = _resolve_ft_chain(("Page", "non_existent_attr"))
        assert obj is None
        assert missing == "non_existent_attr"
        assert idx == 1


# ===========================================================================
# _has_var_keyword
# ===========================================================================


class TestHasVarKeyword:
    def test_true_when_var_keyword(self):
        sig = inspect.signature(lambda *args, **kwargs: None)  # noqa: ARG005
        assert _has_var_keyword(sig) is True

    def test_false_without_var_keyword(self):
        sig = inspect.signature(lambda a, b: None)  # noqa: ARG005
        assert _has_var_keyword(sig) is False

    def test_false_empty(self):
        sig = inspect.signature(lambda: None)  # noqa: ARG005
        assert _has_var_keyword(sig) is False


# ===========================================================================
# _resolve_signature
# ===========================================================================


class TestResolveSignature:
    def test_class_signature(self):
        sig = _resolve_signature(ft.Container)
        assert sig is not None
        assert "content" in sig.parameters

    def test_callable_signature(self):
        sig = _resolve_signature(ft.run)
        assert sig is not None
        assert "main" in sig.parameters

    def test_uncallable_returns_none(self):
        sig = _resolve_signature(42)
        assert sig is None


# ===========================================================================
# _mro_dataclass_fields
# ===========================================================================


class TestMroDataclassFields:
    def test_control_has_fields(self):
        fields = _mro_dataclass_fields(ft.Container)
        assert fields is not None
        assert "content" in fields

    def test_value_type_has_fields(self):
        fields = _mro_dataclass_fields(ft.Alignment)
        assert fields is not None

    def test_enum_returns_none(self):
        fields = _mro_dataclass_fields(ft.AnimationCurve)
        assert fields is None


# ===========================================================================
# _mro_annotations
# ===========================================================================


class TestMroAnnotations:
    def test_control_has_annotations(self):
        annotations = _mro_annotations(ft.Container)
        assert annotations is not None

    def test_enum_returns_none(self):
        annotations = _mro_annotations(ft.AnimationCurve)
        assert annotations is None


# ===========================================================================
# _resolve_typed_target
# ===========================================================================


class TestResolveTypedTarget:
    def test_simple_var(self):
        node = ast.Attribute(value=ast.Name(id="page"), attr="go")
        assert _resolve_typed_target(node) == ("page", "go")

    def test_self_attr(self):
        node = ast.Attribute(
            value=ast.Attribute(value=ast.Name(id="self"), attr="page"),
            attr="navigation_bar",
        )
        assert _resolve_typed_target(node) == ("self.page", "navigation_bar")

    def test_ft_prefix_returns_ft(self):
        node = ast.Attribute(value=ast.Name(id="ft"), attr="Page")
        assert _resolve_typed_target(node) == ("ft", "Page")

    def test_non_self_attr_chain_returns_none(self):
        node = ast.Attribute(
            value=ast.Attribute(value=ast.Name(id="other"), attr="x"),
            attr="y",
        )
        assert _resolve_typed_target(node) is None


# ===========================================================================
# _get_flet_imports (AST-based)
# ===========================================================================


class TestGetFletImports:
    def test_import_flet_as_ft(self):
        tree = ast.parse("import flet as ft")
        direct, prefixed = _get_flet_imports(tree)
        assert direct == {"ft": "flet"}
        assert prefixed == {}

    def test_from_flet_import(self):
        tree = ast.parse("from flet import Page, Text")
        direct, prefixed = _get_flet_imports(tree)
        assert prefixed == {"Page": "flet.Page", "Text": "flet.Text"}

    def test_mixed_imports(self):
        tree = ast.parse("import flet as ft\nfrom flet.controls import Container")
        direct, prefixed = _get_flet_imports(tree)
        assert direct == {"ft": "flet"}
        assert prefixed == {"Container": "flet.controls.Container"}

    def test_non_flet_import_ignored(self):
        tree = ast.parse("import os\nfrom datetime import datetime")
        direct, prefixed = _get_flet_imports(tree)
        assert direct == {}
        assert prefixed == {}


# ===========================================================================
# _rel
# ===========================================================================


class TestRel:
    def test_relative_path(self):
        result = _rel(SRC_DIR / "app.py")
        assert result == "src\\app.py" or result == "src/app.py"

    def test_nested_path(self):
        result = _rel(SRC_DIR / "UI" / "components" / "status_card.py")
        assert "UI" in result and "status_card.py" in result

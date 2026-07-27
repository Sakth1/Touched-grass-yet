"""Verify all Flet API usage matches the installed flet version.

Scans every .py file under src/, parses it with AST, and checks that:
  1. Every ft.X.Y attribute chain exists in the installed flet module
  2. Every keyword argument in ft.X(k=v) calls matches the __init__ signature
  3. Both ``import flet as ft`` and ``from flet import X`` patterns are handled
  4. No ``DeprecationWarning`` or ``FutureWarning`` when accessing ft.X or constructing ft.X
  5. Every ft.X used appears in ft.__all__ (public API contract)
  6. DeprecationWarning on function calls (not just constructors)
  7. Method calls and property assignments on type-tracked variables
     (e.g. ``page.go()``, ``page.title = …``) match the flet type's API

Fails CI on any mismatch (hard compatibility gate).
"""

from __future__ import annotations

import ast
import inspect
import warnings
from pathlib import Path

import flet as ft
import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
SKIP_DIRS = {"__pycache__", ".venv", "node_modules", ".git"}


# ═══════════════════════════════════════════════════════════════
#  AST helpers — discover flet imports and resolve dotted chains
# ═══════════════════════════════════════════════════════════════


def _get_flet_imports(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    """Return (direct_imports, prefixed_imports) from module-level imports.

    *direct_imports* — local name → full dotted flet path.
        ``import flet as ft``            → ``{"ft": "flet"}``
        ``import flet``                  → ``{"flet": "flet"}``
        ``import flet.controls as ctrl`` → ``{"ctrl": "flet.controls"}``

    *prefixed_imports* — local name → full dotted path (from ``from`` imports).
        ``from flet import X``           → ``{"X": "flet.X"}``
        ``from flet.controls import Y``  → ``{"Y": "flet.controls.Y"}``
    """
    direct: dict[str, str] = {}
    prefixed: dict[str, str] = {}

    for node in ast.walk(tree):
        match node:
            case ast.Import():
                for alias in node.names:
                    if alias.name == "flet" or alias.name.startswith("flet."):
                        local = alias.asname or alias.name
                        direct[local] = alias.name
            case ast.ImportFrom():
                if node.module and (node.module == "flet" or node.module.startswith("flet.")):
                    for alias in node.names:
                        prefixed[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return direct, prefixed


def _resolve_attr_chain(node: ast.AST) -> list[str] | None:
    """Walk ``a.b.c`` → ``["a", "b", "c"]``.  Returns ``None`` for non-attribute nodes."""
    match node:
        case ast.Name():
            return [node.id]
        case ast.Attribute():
            parts = _resolve_attr_chain(node.value)
            if parts is not None:
                parts.append(node.attr)
                return parts
    return None


def _to_ft_chain(
    local_chain: list[str],
    direct_imports: dict[str, str],
    prefixed_names: dict[str, str],
) -> tuple[str, ...] | None:
    """Normalise a local-name chain to a flet-relative dotted tuple.

    =============================== =============================== ============================
    Import form                     Local chain                     Result
    =============================== =============================== ============================
    ``import flet as ft``           ``["ft", "Foo", "Bar"]``        ``("Foo", "Bar")``
    ``import flet.controls as ctrl`` ``["ctrl", "X"]``               ``("controls", "X")``
    ``from flet import X``          ``["X", "Y"]``                  ``("X", "Y")``
    ``from flet.controls import X``  ``["X", "Z"]``                 ``("controls", "X", "Z")``
    =============================== =============================== ============================
    """
    root = local_chain[0]
    if root in direct_imports:
        flet_path = direct_imports[root].split(".")
        if flet_path[0] == "flet":
            return tuple(flet_path[1:] + local_chain[1:])
        return None
    if root in prefixed_names:
        prefixed = prefixed_names[root].split(".")
        if prefixed[0] == "flet":
            return tuple(prefixed[1:] + local_chain[1:])
    return None


def _has_flet_imports(direct_imports: dict[str, str], prefixed_names: dict[str, str]) -> bool:
    return bool(direct_imports) or bool(prefixed_names)


def _resolve_typed_target(node: ast.Attribute) -> tuple[str, str] | None:
    """Extract ``(var_name, member_name)`` from an attribute chain on a typed variable.

    ``page.title``     → ``("page", "title")``
    ``self.page.go``   → ``("self.page", "go")``
    ``ft.SomeThing``   → ``("ft", "SomeThing")`` (won't match *type_map*)
    """
    if isinstance(node.value, ast.Name):
        return node.value.id, node.attr
    if (
        isinstance(node.value, ast.Attribute)
        and isinstance(node.value.value, ast.Name)
        and node.value.value.id == "self"
    ):
        return f"self.{node.value.attr}", node.attr
    return None


# ═══════════════════════════════════════════════════════════════
#  Runtime resolution helpers
# ═══════════════════════════════════════════════════════════════


def _resolve_ft_chain(chain: tuple[str, ...]) -> tuple[object, str | None, int | None]:
    """Walk a flet-relative chain against the installed ``flet`` module.

    Returns ``(resolved_obj, None, None)`` on success,
    or ``(None, missing_part, index)`` on first failure.
    """
    obj: object = ft
    for i, part in enumerate(chain):
        if hasattr(obj, part):
            obj = getattr(obj, part)
        else:
            return None, part, i
    return obj, None, None


def _get_valid_params(obj: object) -> set[str] | None:
    """Return keyword-accepting parameter names for a callable or class.

    Resolution order:
    1. If ``__init__`` has **no** ``**kwargs`` → return named params directly.
    2. If ``**kwargs`` present → walk MRO for ``__dataclass_fields__``.
    3. Fallback → walk MRO for ``__annotations__``.
    4. None of the above → return ``None`` (cannot validate, skip).
    """
    sig = _resolve_signature(obj)
    if sig is None:
        return set()

    named = {p for p in sig.parameters if p not in ("self",)}
    if not _has_var_keyword(sig):
        return named

    if isinstance(obj, type):
        fields = _mro_dataclass_fields(obj)
        if fields is not None:
            return fields
        ann = _mro_annotations(obj)
        if ann is not None:
            return ann

    return None


def _resolve_signature(obj: object) -> inspect.Signature | None:
    """Unified signature retriever for classes and callables."""
    try:
        if isinstance(obj, type):
            return inspect.signature(obj.__init__)
        if callable(obj):
            return inspect.signature(obj)
    except (ValueError, TypeError):
        return None


def _has_var_keyword(sig: inspect.Signature) -> bool:
    """True if the signature accepts ``**kwargs`` (VAR_KEYWORD)."""
    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values())


def _mro_dataclass_fields(obj: type) -> set[str] | None:
    """Collect ``__dataclass_fields__`` from the whole MRO chain."""
    fields: set[str] = set()
    for cls in obj.__mro__:
        if hasattr(cls, "__dataclass_fields__"):
            fields.update(cls.__dataclass_fields__)
    return fields if fields else None


def _mro_annotations(obj: type) -> set[str] | None:
    """Collect ``__annotations__`` from the whole MRO chain."""
    ann: set[str] = set()
    for cls in obj.__mro__:
        if hasattr(cls, "__annotations__"):
            ann.update(cls.__annotations__)
    return ann if ann else None


# ═══════════════════════════════════════════════════════════════
#  Trial construction / call helpers
# ═══════════════════════════════════════════════════════════════


_ENTRY_POINT_FUNCS = frozenset({"run", "run_async", "app", "app_async"})


def _trial_construct_or_call(
    obj: object,
    chain: tuple[str, ...],
    lineno: int,
    issues: list[str],
    py_file: Path,
    kws: list[str],
    valid: set[str],
) -> None:
    """Try constructing (type) or calling (function) *obj* with ``None`` kwargs.

    Catches ``DeprecationWarning`` / ``FutureWarning`` emitted by the constructor/call.
    Skips functions known to start event loops (``run``, ``app``, …).
    """
    is_ctor = isinstance(obj, type)
    if not is_ctor and not callable(obj):
        return

    # ── Safety: skip entry-point functions that launch the app ──
    if not is_ctor:
        func_name = getattr(obj, "__name__", "")
        if func_name in _ENTRY_POINT_FUNCS:
            return

    init_kwargs = {kw: None for kw in kws if kw in valid}
    if not init_kwargs:
        return

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            obj(**init_kwargs)
        except Exception:
            pass

    for w in caught:
        if issubclass(w.category, (DeprecationWarning, FutureWarning)):
            dotted = ".".join(chain)
            label = "constructor" if is_ctor else "call"
            issues.append(
                f"{_rel(py_file)}:{lineno}  "
                f"ft.{dotted} {label} is deprecated: {w.message}"
            )


# ═══════════════════════════════════════════════════════════════
#  Type inference — track which local vars hold flet types
# ═══════════════════════════════════════════════════════════════


def _build_type_map(
    tree: ast.AST,
    direct_imports: dict[str, str],
    prefixed_names: dict[str, str],
) -> dict[str, tuple[str, ...]]:
    """Map local variable names to their flet type chains.

    Sources (in priority order):
    1. Annotated function params: ``def f(page: ft.Page)``
    2. Self-attribute propagation from typed params: ``self.page = page`` (in ``__init__``)
    3. Self-attribute from direct construction: ``self._container = ft.Container(...)``
    """
    type_map: dict[str, tuple[str, ...]] = {}

    # Step 1 — annotated params from every function / method
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation:
                    chain = _resolve_attr_chain(arg.annotation)
                    if chain:
                        ft_chain = _to_ft_chain(chain, direct_imports, prefixed_names)
                        if ft_chain:
                            type_map[arg.arg] = ft_chain

    # Step 2 — self.xxx assignments inside __init__
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    for stmt in ast.walk(item):
                        if isinstance(stmt, ast.Assign):
                            for target in stmt.targets:
                                if (
                                    isinstance(target, ast.Attribute)
                                    and isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                ):
                                    # self.xxx = param_name (param known from step 1)
                                    if isinstance(stmt.value, ast.Name) and stmt.value.id in type_map:
                                        type_map[f"self.{target.attr}"] = type_map[stmt.value.id]
                                    # self.xxx = ft.Y(...)
                                    elif isinstance(stmt.value, ast.Call):
                                        call_root = _resolve_attr_chain(stmt.value.func)
                                        if call_root:
                                            ft_chain = _to_ft_chain(call_root, direct_imports, prefixed_names)
                                            if ft_chain:
                                                type_map[f"self.{target.attr}"] = ft_chain
    return type_map


def _collect_typed_usages(
    tree: ast.AST,
    type_map: dict[str, tuple[str, ...]],
) -> tuple[list[tuple[tuple[str, ...], str, int]], list[tuple[tuple[str, ...], str, int]]]:
    """Collect method calls and property assignments on type-tracked vars.

    Returns ``(method_calls, prop_assigns)`` where each entry is
    ``(ft_type_chain, member_name, lineno)``.

    Only yields entries for variables present in *type_map*.
    """
    method_calls: list[tuple[tuple[str, ...], str, int]] = []
    prop_assigns: list[tuple[tuple[str, ...], str, int]] = []

    for node in ast.walk(tree):
        match node:
            case ast.Call():
                if isinstance(node.func, ast.Attribute):
                    info = _resolve_typed_target(node.func)
                    if info and info[0] in type_map:
                        method_calls.append((type_map[info[0]], info[1], node.lineno))

            case ast.Assign():
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        info = _resolve_typed_target(target)
                        if info and info[0] in type_map:
                            prop_assigns.append((type_map[info[0]], info[1], target.lineno))

    return method_calls, prop_assigns


# ═══════════════════════════════════════════════════════════════
#  Per-file AST collector
# ═══════════════════════════════════════════════════════════════


def _collect_usages(
    filepath: Path,
    direct_imports: dict[str, str],
    prefixed_names: dict[str, str],
) -> tuple[set[tuple[str, ...]], list[tuple[tuple[str, ...], list[str], int]]]:
    """Collect all ``ft.X.Y`` attribute chains and ``ft.X(k=v)`` calls in a file.

    Returns ``(attrs, calls)`` where:
    * *attrs* — set of unique flet-relative chains found anywhere in the file
    * *calls* — ``(chain, keyword_arg_names, lineno)`` for every call to an ``ft.*`` target
    """
    with open(filepath, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    attrs: set[tuple[str, ...]] = set()
    calls: list[tuple[tuple[str, ...], list[str], int]] = []

    class _Visitor(ast.NodeVisitor):
        def visit_Attribute(self, node: ast.Attribute) -> None:
            chain = _resolve_attr_chain(node)
            if chain:
                ft_chain = _to_ft_chain(chain, direct_imports, prefixed_names)
                if ft_chain is not None:
                    attrs.add(ft_chain)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            if isinstance(func, (ast.Attribute, ast.Name)):
                chain = _resolve_attr_chain(func)
                if chain:
                    ft_chain = _to_ft_chain(chain, direct_imports, prefixed_names)
                    if ft_chain is not None:
                        kws = [kw.arg for kw in node.keywords if kw.arg is not None]
                        calls.append((ft_chain, kws, node.lineno))
            self.generic_visit(node)

    _Visitor().visit(tree)
    return attrs, calls


# ═══════════════════════════════════════════════════════════════
#  Library adapter — isolate flet-specific operations
#  ═══════════════════════════════════════════════════════════════
#  To add support for a new library (e.g. Plotly, DuckDB):
#  1. Create ``PlotlyAdapter`` / ``DuckDBAdapter`` with the same interface
#  2. Pass it to each stage function instead of using ``ft`` directly
# ═══════════════════════════════════════════════════════════════


class _FletAdapter:
    """Wraps flet-specific resolution and param discovery."""

    root = ft
    all_names = ft.__all__

    @staticmethod
    def resolve(chain: tuple[str, ...]) -> tuple[object, str | None, int | None]:
        return _resolve_ft_chain(chain)

    @staticmethod
    def valid_params(obj: object) -> set[str] | None:
        return _get_valid_params(obj)


# ═══════════════════════════════════════════════════════════════
#  Stage passes — each validates one aspect of the API contract
# ═══════════════════════════════════════════════════════════════


def _check_attr_existence(
    adapter: _FletAdapter,
    attrs: set[tuple[str, ...]],
    py_file: Path,
) -> list[str]:
    """Stage 1: every ``ft.X.Y`` chain must exist in the installed module."""
    issues: list[str] = []
    for chain in sorted(attrs, key=lambda c: (len(c), c)):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _, missing, idx = adapter.resolve(chain)

        for w in caught:
            if issubclass(w.category, (DeprecationWarning, FutureWarning)):
                dotted = ".".join(chain)
                issues.append(
                    f"{_rel(py_file)}  ft.{dotted} is deprecated: {w.message}"
                )

        if missing:
            prefix = ".".join(chain[:idx]) if idx else ""
            dotted = f"{prefix}.{missing}" if prefix else missing
            issues.append(f"{_rel(py_file)}  ft.{dotted} does not exist")
    return issues


def _check_all_membership(
    adapter: _FletAdapter,
    attrs: set[tuple[str, ...]],
    py_file: Path,
) -> list[str]:
    """Stage 2: every ``ft.X`` root name must appear in ``ft.__all__``."""
    issues: list[str] = []
    for chain in sorted(attrs, key=lambda c: (len(c), c)):
        if chain[0] not in adapter.all_names:
            dotted = ".".join(chain)
            issues.append(
                f"{_rel(py_file)}  "
                f"ft.{dotted} is not in ft.__all__ — may be unstable"
            )
    return issues


def _check_typed_calls(
    adapter: _FletAdapter,
    method_calls: list[tuple[tuple[str, ...], str, int]],
    py_file: Path,
) -> list[str]:
    """Stage 3: method calls on type-tracked vars (``page.go()``) must exist."""
    issues: list[str] = []
    for ft_type, method, lineno in method_calls:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            obj, missing, idx = adapter.resolve(ft_type)

        for w in caught:
            if issubclass(w.category, (DeprecationWarning, FutureWarning)):
                dotted = ".".join(ft_type)
                issues.append(
                    f"{_rel(py_file)}:{lineno}  "
                    f"ft.{dotted} is deprecated (base type for method '{method}')"
                )

        if missing:
            prefix = ".".join(ft_type[:idx]) if idx else ""
            dotted = f"{prefix}.{missing}" if prefix else missing
            issues.append(
                f"{_rel(py_file)}:{lineno}  "
                f"ft.{dotted} does not exist (base type for method '{method}')"
            )
        elif not hasattr(obj, method):
            dotted = ".".join(ft_type)
            issues.append(
                f"{_rel(py_file)}:{lineno}  "
                f"ft.{dotted}.{method}() does not exist"
            )
    return issues


def _check_typed_assigns(
    adapter: _FletAdapter,
    prop_assigns: list[tuple[tuple[str, ...], str, int]],
    py_file: Path,
) -> list[str]:
    """Stage 4: property assignments on type-tracked vars (``page.title = …``) must exist."""
    issues: list[str] = []
    for ft_type, prop, lineno in prop_assigns:
        obj, missing, idx = adapter.resolve(ft_type)
        if missing:
            prefix = ".".join(ft_type[:idx]) if idx else ""
            dotted = f"{prefix}.{missing}" if prefix else missing
            issues.append(
                f"{_rel(py_file)}:{lineno}  "
                f"ft.{dotted} does not exist (base type for property '{prop}')"
            )
        else:
            if hasattr(obj, prop):
                continue
            valid_params = adapter.valid_params(obj)
            if valid_params is not None and prop in valid_params:
                continue
            dotted = ".".join(ft_type)
            issues.append(
                f"{_rel(py_file)}:{lineno}  "
                f"ft.{dotted}.{prop} does not exist"
            )
    return issues


def _check_calls(
    adapter: _FletAdapter,
    calls: list[tuple[tuple[str, ...], list[str], int]],
    py_file: Path,
) -> list[str]:
    """Stage 5+6: keyword-arg validity + trial construction deprecation."""
    issues: list[str] = []
    for chain, kws, lineno in sorted(calls, key=lambda c: (c[2], c[0])):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            obj, _, _ = adapter.resolve(chain)

        for w in caught:
            if issubclass(w.category, (DeprecationWarning, FutureWarning)):
                dotted = ".".join(chain)
                issues.append(
                    f"{_rel(py_file)}:{lineno}  "
                    f"ft.{dotted} is deprecated: {w.message}"
                )

        if obj is None or not kws:
            continue
        valid = adapter.valid_params(obj)
        if valid is None:
            continue
        for kw in kws:
            if kw not in valid:
                dotted = ".".join(chain)
                issues.append(
                    f"{_rel(py_file)}:{lineno}  "
                    f"ft.{dotted}({kw}=...) is not a valid parameter"
                )

        _trial_construct_or_call(obj, chain, lineno, issues, py_file, kws, valid)
    return issues


# ═══════════════════════════════════════════════════════════════
#  Test — orchestrates stages
# ═══════════════════════════════════════════════════════════════


def test_flet_api_compatibility():
    """Every ``ft.X.Y`` and ``ft.X(param=…)`` in ``src/`` must match installed flet."""
    py_files = sorted(SRC_DIR.rglob("*.py"))
    issues: list[str] = []

    for py_file in py_files:
        if any(part in SKIP_DIRS for part in py_file.parts):
            continue
        if not py_file.is_file():
            continue

        try:
            tree = ast.parse(py_file.read_bytes())
        except SyntaxError as exc:
            issues.append(f"{_rel(py_file)}: SyntaxError — {exc}")
            continue

        direct_imports, prefixed_names = _get_flet_imports(tree)
        if not _has_flet_imports(direct_imports, prefixed_names):
            continue

        attrs, calls = _collect_usages(py_file, direct_imports, prefixed_names)
        type_map = _build_type_map(tree, direct_imports, prefixed_names)
        method_calls, prop_assigns = _collect_typed_usages(tree, type_map)

        adapter = _FletAdapter()
        issues += _check_attr_existence(adapter, attrs, py_file)
        issues += _check_all_membership(adapter, attrs, py_file)
        issues += _check_typed_calls(adapter, method_calls, py_file)
        issues += _check_typed_assigns(adapter, prop_assigns, py_file)
        issues += _check_calls(adapter, calls, py_file)

    if issues:
        unique = sorted(set(issues))
        header = f"Found {len(unique)} Flet API compatibility issue(s):\n"
        body = "\n".join(f"  {i+1}. {m}" for i, m in enumerate(unique))
        pytest.fail(header + body)


def _rel(path: Path) -> str:
    """Short relative path from repo root."""
    return str(path.relative_to(SRC_DIR.parent))

"""Callable sweep: every public function, constructor and method must run.

For each module discovered under ``src/``, every public callable is invoked
with values derived from its own signature (annotations + defaults), including
None/empty boundary variants where the signature admits them. Async callables
run under a 2s deadline. Any exception outside the documented input-validation
families, and any Python warning emitted, fails the suite — the callable is
logged so failures are instantly debuggable.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import logging
import types
import typing
import warnings

import pytest
from sweep_helpers import (
    build_call_kwargs,
    discover_module_names,
    expected_exception,
    public_callables,
    public_methods,
)

logger = logging.getLogger(__name__)

_TIMEOUT_S = 2.0
_log: list[str] = []


def _invoke(target, kwargs: dict) -> None:
    label = f"{target.__module__}.{getattr(target, '__qualname__', target.__name__)}"
    if inspect.isasyncgenfunction(target):
        return
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            result = target(**kwargs)
            if inspect.iscoroutine(result):
                asyncio.run(asyncio.wait_for(result, timeout=_TIMEOUT_S))
        except asyncio.TimeoutError:
            _log.append(f"{label} HUNG longer than {_TIMEOUT_S}s")
        except BaseException as exc:
            if not expected_exception(target, exc):
                _log.append(f"{label}({kwargs}) raised {type(exc).__name__}: {exc}")
    for w in caught:
        _log.append(f"{label} emitted warning {w.category.__name__}: {w.message}")


def _boundary_variants(func, kwargs: dict) -> list[dict]:
    """None-variants for parameters whose signature admits ``None``."""
    variants: list[dict] = []
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return variants
    for param in signature.parameters.values():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if param.name in ("self", "cls") or param.name not in kwargs:
            continue
        sample = kwargs[param.name]
        if sample is None:
            continue
        origin = getattr(param.annotation, "__origin__", None)
        allows_none = param.default is None or origin in (typing.Union, types.UnionType)
        if allows_none:
            variant = dict(kwargs)
            variant[param.name] = None
            variants.append(variant)
    return variants


def _sweep_callable(target, kwargs: dict) -> None:
    _invoke(target, kwargs)
    for variant in _boundary_variants(target, kwargs):
        _invoke(target, variant)


def _sweep_function(func) -> None:
    _sweep_callable(func, build_call_kwargs(func))


def _sweep_class(cls) -> None:
    label = f"{cls.__module__}.{cls.__name__}"
    kwargs = build_call_kwargs(cls)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            instance = cls(**kwargs)
        except BaseException as exc:
            if not expected_exception(cls, exc):
                _log.append(f"{label}({kwargs}) raised {type(exc).__name__}: {exc}")
            return
    for w in caught:
        _log.append(
            f"{label} construction emitted warning {w.category.__name__}: {w.message}"
        )

    for name, _member in public_methods(cls):
        member = getattr(cls, name)
        target = (
            member.__func__
            if isinstance(member, (classmethod, staticmethod))
            else getattr(instance, name)
        )
        _sweep_callable(target, build_call_kwargs(target))


def test_every_public_callable_runs(chdir_tmp):
    modules = [importlib.import_module(name) for name in discover_module_names()]
    assert modules, "module discovery found nothing under src/"

    for module in modules:
        for _name, obj in public_callables(module):
            if inspect.isclass(obj):
                _sweep_class(obj)
            else:
                _sweep_function(obj)

    if _log:
        pytest.fail("Callable sweep found problems:\n\n" + "\n".join(_log))

# Deprecation Policy

## Flet API Compatibility Gate

The test `tests/test_flet_api_compat.py` enforces a **hard compatibility gate** between
`src/` code and the installed `flet` version. It catches:

1. **Missing attributes** — `ft.X.Y` no longer exists
2. **Invalid keyword arguments** — `ft.X(k=v)` where `k` is not a valid parameter
3. **Deprecated constructors/calls** — `DeprecationWarning` emitted during trial construction
4. **Public API instability** — `ft.X` used but not listed in `ft.__all__`
5. **Type-tracked method/property breakage** — `page.go()` / `page.title = ...` on typed variables

## What triggers a failure

| Condition | Severity | Action |
|---|---|---|
| `ft.X` does not exist | **BREAKING** | Fix: replace with current API |
| `ft.X(k=...)` param missing | **BREAKING** | Fix: use valid param name |
| `ft.X` not in `__all__` | **WARNING** | Fix: use public API or add to `__all__` |
| `DeprecationWarning` from flet | **BREAKING** (error) | Fix: migrate to replacement API |
| `ft.Type.method()` missing | **BREAKING** | Fix: use correct method name |
| `ft.Type.prop = ...` missing | **BREAKING** | Fix: use correct property name |

## DeprecationWarning → Error

`conftest.py` globally turns `DeprecationWarning` into test errors. This means:

- Any flet deprecation (even outside the compat test) fails the build
- Deprecations must be fixed, not silenced
- Use `warnings.catch_warnings` in tests that knowingly trigger deprecations

## Keeping up with Flet releases

1. **Upgrade flet** in `pyproject.toml`
2. Run `python scripts/save_flet_snapshot.py` to update `api-snapshot.json`
3. Run `pytest tests/` to check for API breaks
4. Fix any breakage before committing

## Adding support for a new library

See `_FletAdapter` in `tests/test_flet_api_compat.py`. Implement the same interface
(`resolve`, `valid_params`, `all_names`) for the new library and pass it to each
stage function.

## When to remove a snapshot

The `api-snapshot.json` baseline should be updated after every intentional flet upgrade.
Compare `scripts/check_flet_snapshot.py` output against the changelog to verify
that differences are expected.

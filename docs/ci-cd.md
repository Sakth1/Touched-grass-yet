# CI/CD Pipeline

## Architecture

Single unified workflow (`.github/workflows/ci.yml`) with strict job dependency chain:

```
push (master/dev) or PR
        │
  ┌─────▼─────┐
  │   lint    │  ruff check src/ tests/
  └─────┬─────┘
        │
  ┌─────▼─────┐
  │   test    │  pytest (full suite, fetch-depth: 0)
  └─────┬─────┘
        │
  ┌─────▼──────────┐
  │ detect-version │  only on master push
  │    -bump       │  compares pyproject.toml version
  └─────┬──────────┘
        │ (if version bumped)
  ┌─────▼──────┐
  │   build    │  Windows EXE + Android APK (parallel)
  └─────┬──────┘
        │
  ┌─────▼──────┐
  │  publish   │  GitHub Release + asset upload
  └────────────┘
```

## Fail-Safe Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| No release if tests fail | `detect-version-bump` requires `test` |
| No binary build if tests fail | `build-*` requires `test` |
| No release without version bump | `detect-version-bump` checks pyproject.toml |
| No partially completed release | `publish-release` requires all builds |
| Tests work in shallow clones | Migration tests embed schema SQL, no `git show` |

## Release Process

1. Bump `version` in `pyproject.toml` on `master`.
2. Push triggers `ci.yml`.
3. `lint` → `test` → `detect-version-bump` detects increase.
4. `build-windows` and `build-android` run in parallel.
5. `publish-release` creates GitHub release and attaches binaries.

## Troubleshooting

### Tests fail locally but pass in CI
- Check `SCHEMA_VERSION` against `_run_migrations()` — stale migration code is the most common cause.
- Run `pytest -v --tb=long tests/test_storage.py -k "TestSchemaMigration"` to isolate.

### Tests fail in CI but pass locally
- CI uses shallow clone (`fetch-depth: 0` in lint/test jobs ensures full history).
- CI runs on Windows Server 2022, Python 3.12.x (patch may differ).
- Check for environment-dependent behavior (file paths, permissions, timezone).

## Auto-Update Support

The build pipeline must generate installers compatible with v0.5.0's silent auto-update system:

| Platform | Update Mechanism | CI Requirements |
|----------|-----------------|-----------------|
| Windows | Inno Setup silent install (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART`) | Inno Setup script must set `DisableDirPage=auto`, `DisableProgramGroupPage=auto`, verify `UsePreviousAppDir=yes` |
| Android | APK download + `ACTION_VIEW` install intent | Standard APK build is sufficient (install intent handled client-side) |

After auto-update, user data in `%APPDATA%\Unscreen\` (Windows) or app internal storage (Android) is preserved — only program files are replaced.

### Release not created
- Verify `version` in `pyproject.toml` was increased.
- Check `detect-version-bump` step output in CI logs.
- Ensure push was to `master` branch (not `dev`).

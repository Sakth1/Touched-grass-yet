# Android Flet build failure: `lz4`

Date: 2026-08-04

## Summary

The latest GitHub Actions `CI` run failed in the Android job during `flet build apk`, before Flutter produced an APK. The failing step ran:

```text
flet build apk --yes --compile-packages --skip-flutter-doctor --no-rich-output
```

Serious Python then invoked pip for Android `arm64-v8a` with `--only-binary :all:` and tried to install `lz4 >=4.3`; pip reported `ERROR: Could not find a version that satisfies the requirement lz4>=4.3 (from versions: none)`.

Sources: latest failed run `30913738363`, job `build-android`, step `Build Android APK` (`gh run view 30913738363 --log-failed`), and the workflow command in [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).

## Evidence

- The Android CI job installs the project and Flet CLI, then runs `flet build apk --yes --compile-packages --skip-flutter-doctor --no-rich-output`. Source: [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml).
- The project declares shared dependencies in `[project].dependencies`, including `flet`, `orjson`, `psutil`, `publicsuffixlist`, `rich`, and Windows-marked `lz4` / `pywinauto`. Source: [`pyproject.toml`](../../pyproject.toml).
- The project also declares `[tool.flet.android].dependencies` with Android-specific packaging dependencies: `flet`, `orjson`, `psutil`, `pyjnius`, and `rich`. Source: [`pyproject.toml`](../../pyproject.toml).
- Flet documents that app dependencies are resolved from `[project].dependencies`, and platform-specific `[tool.flet.<PLATFORM>].dependencies` are appended rather than replacing the project dependency list. Source: [Flet publishing docs, App dependencies](https://flet.dev/docs/publish/).
- Flet documents that `flet build` packages the Python app using `serious_python package` and installs dependencies from `pypi.org` and `pypi.flet.dev`. Source: [Flet publishing docs, How it works](https://flet.dev/docs/publish/).
- Serious Python documents that Flet drives Serious Python automatically, and that dependencies are passed to pip via the packaging command. Source: [serious_python package docs](https://pub.dev/packages/serious_python).
- Flet/Serious Python mobile packaging is intentionally binary-first: Flet says mobile and web packaging install binary wheels by default, with `source_packages` mainly for pure-Python sdists; Serious Python's changelog says binary-package misses do not trigger source compilation. Sources: [Flet publishing docs, Source packages](https://flet.dev/docs/publish/) and [serious_python changelog 0.8.0](https://pub.dev/packages/serious_python/changelog).
- Flet's Android docs say non-pure Python packages must have prebuilt wheels for Android. Source: [Flet Android publishing docs](https://flet.dev/docs/publish/android/).
- Flet's current built-in binary package list for Android/iOS includes `orjson`, `psutil`, and `pyjnius`, but does not list `lz4`. Source: [Flet built-in binary package list](https://flet.dev/docs/reference/binary-packages-android-ios/).
- PyPI's `lz4` 4.4.5 files include source plus CPython wheels for Windows, macOS, and manylinux platforms; the page does not list Android wheels. Source: [PyPI `lz4` project page](https://pypi.org/project/lz4/).
- In this repo, `lz4.block` is imported only inside the Windows Firefox session recovery path, and the import is optional. Source: [`src/core/collectors/windows/url_extractor.py`](../../src/core/collectors/windows/url_extractor.py).

## Root Cause

The Android build is trying to package `lz4` even though no Android wheel for `lz4` is available from either Flet's mobile wheel index or PyPI. Because Serious Python invokes pip in binary-only mode for Android, pip cannot fall back to the `lz4` source distribution. The failure is therefore a dependency packaging mismatch, not an Android SDK, Flutter, signing, or source-code compile failure.

## Solution Options

1. Remove `lz4` from the dependency set that Flet sees for Android. Since this repo only uses `lz4` for Windows Firefox recovery, keep it out of Android packaging. A practical shape is to move Windows-only dependencies into an optional Windows extra and make the Windows CI install that extra, while Android installs only the cross-platform/Android dependencies.

2. If Android truly needs `lz4` later, request or add an Android/iOS binary wheel recipe through Flet's mobile package process. Flet documents `pypi.flet.dev` as the mobile binary wheel source and points unavailable binary-package requests to Flet Discussions / Mobile Forge.

3. Do not treat `--source-packages lz4` as the primary fix. Flet documents source packages as useful mainly for pure-Python packages without wheels, while `lz4` is a native binding package and the Android failure is specifically caused by a missing target binary wheel.

## Recommended Next Step

Keep the Android build dependency list free of `lz4`. The narrowest maintainable fix is to make `lz4` a Windows-only optional install path and ensure the Android packaging path does not inherit it from `[project].dependencies`.

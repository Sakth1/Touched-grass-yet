# ADR-0001: Collection parity and foreground dual-track design v2

**Status:** Accepted (updated v0.4.0)

## Changes in v0.4.0

The original design used pulse-merge at write time to infer sessions from consecutive observations. This produced:
- 28% zero-duration rows on Windows (title changes and app switches break merge)
- 100% zero-duration rows on Android (durations dict never matches between ticks)
- Misleading duration on power/afk (artifacts of poll interval)

The updated architecture separates **observations** (raw poll output, no duration) from **sessions** (computed by `Sessionizer` as a post-process). Duration is computed from session start/end timestamps, never from pulse-merge.

## Design

AFK and Power watchers share identical schemas (`status`/`idle_seconds` and `battery_pct`/`charging`) across Windows and Android because both platforms provide equivalent low-level sensor data through different APIs (Win32 ctypes vs. pyjnius). Foreground schemas necessarily diverge because Windows exposes process/title info while Android exposes package names and usage events — they measure fundamentally different things.

For Android, the foreground watcher uses a dual-track strategy: real-time usage events (RESUME/PAUSE) for accurate per-interval durations, synced against cumulative usage stats every tick to prevent stale baselines. A `_session_reported` dict carries forward partially-counted PAUSED durations across tick boundaries to avoid double-counting. Screen-on fallback keeps reporting the last known app when events are temporarily unavailable, rather than dropping to idle.

Android foreground's `data.durations` field carries system-level millisecond-precise durations. The `Sessionizer` uses these values (when available) instead of computing from timestamps.

AFK and Power are **time-series observations** — they have no session representation and no duration field. Duration is meaningless for state snapshots.

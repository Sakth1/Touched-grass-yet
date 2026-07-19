# ADR-0001: Collection parity and Android foreground dual-track design

**Status:** Accepted

AFK and Power watchers share identical schemas (`status`/`idle_seconds` and `battery_pct`/`charging`) across Windows and Android because both platforms provide equivalent low-level sensor data through different APIs (Win32 ctypes vs. pyjnius). Foreground schemas necessarily diverge because Windows exposes process/title info while Android exposes package names and usage events — they measure fundamentally different things. For Android, the foreground watcher uses a dual-track strategy: real-time usage events (RESUME/PAUSE) for accurate per-interval durations, synced against cumulative usage stats every tick to prevent stale baselines. A `_session_reported` dict carries forward partially-counted PAUSED durations across tick boundaries to avoid double-counting. Screen-on fallback keeps reporting the last known app when events are temporarily unavailable, rather than dropping to idle.

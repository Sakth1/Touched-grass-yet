# Touched Grass Yet

Cross-device app usage timeline tracker. Tracks what application you're using, on which device, and for how long — with idle detection.

**Philosophy**: Track only what matters — foreground app, window title, idle status. No CPU/RAM/network/audio/screenshots.

## Architecture

Watchers poll at fixed intervals and emit **Ticks** (state snapshots). Adjacent identical ticks are merged into sessions during storage.

```
WindowWatcher (2s) ─┐
AfkWatcher    (5s) ─┤── TickBus → Scheduler → Storage → UI
PowerWatcher (60s) ─┘
```

## Run

```bash
uv run flet run           # desktop
uv run flet run --web     # web
```

## Dependencies

apsw, duckdb, flet, orjson, psutil, pywin32, rich

# Touched Grass Yet

Cross-device app usage timeline tracker with idle detection. Privacy-first, local-only, no cloud.

**Tracks:** what app you're using, on which device, for how long, with browser page inference.

**Does NOT track:** CPU, RAM, disk, network, audio, screenshots, clipboard, keystrokes, microphone, camera.

---

## Architecture

```
                   2s                         5s                         60s
            ForegroundWatcher           AfkWatcher              PowerWatcher
            ┌─────────────────┐    ┌───────────────┐      ┌──────────────────┐
            │ WindowAnalyzer  │    │ GetLastInput  │      │ sensors_battery  │
            │  + BrowserAnaly │    │  → idle_secs  │      │  → pct, charging │
            └────────┬────────┘    └───────┬───────┘      └───────┬──────────┘
                     │                     │                       │
                     └─────────────────────┼───────────────────────┘
                                           ▼
                                     TickBus
                                   (async pub/sub)
                                    ┌──┬──┐
                                    │  │  │
                                    ▼  ▼  ▼
                               Storage   UI
                              (APSW)   (Flet)
```

## Data Model

### Tick (unit of collection)

Every watcher emits a `Tick` on each poll cycle. Adjacent ticks with identical data are merged into sessions at write time (pulse-merge, like ActivityWatch).

```python
@dataclass
class Tick:
    id: UUID
    watcher: str        # "foreground" | "afk" | "power"
    timestamp: datetime  # UTC
    data: dict           # watcher-specific payload
```

### Watcher Schemas

| Watcher | Interval | Data | Merge Key |
|---|---|---|---|
| `foreground` | 2s | `{app, title, [browser], [page_title], [inferred_domain]}` | all fields |
| `afk` | 5s | `{status: "active"\|"idle"\|"away", idle_seconds}` | `status` only |
| `power` | 60s | `{battery_pct, charging}` | all fields |

Browser info (`browser`, `page_title`, `inferred_domain`) is populated when the foreground window is a known browser (Chrome, Firefox, Edge, Brave, Opera, Vivaldi). Domain inference is best-effort keyword matching (no real URL access without a browser extension).

## Database Schema

**Location:** `%APPDATA%\TouchedGrassYet\data.db`

**Engine:** SQLite via APSW, WAL journal mode.

### `devices` — device registry (shared across platforms)

```sql
CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,   -- UUID from MachineGuid or generated
    hostname    TEXT,               -- "DESKTOP-A1VV4AH"
    platform    TEXT,               -- "windows" | "android"
    first_seen  TEXT NOT NULL,      -- ISO 8601 UTC
    last_seen   TEXT,               -- updated on each startup
    is_current  INTEGER DEFAULT 0   -- 1 = this machine
);
```

### `events_{short_id}` — per-device event storage

One table per device (8-char prefix of device UUID). Future sync: each device writes to its own table, no ID conflicts.

```sql
CREATE TABLE IF NOT EXISTS events_ea56c63f (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher    TEXT NOT NULL,       -- "foreground" | "afk" | "power"
    timestamp  REAL NOT NULL,       -- Unix epoch seconds (UTC)
    duration   REAL DEFAULT 0,     -- seconds, rounded to 2 decimals
    data       TEXT NOT NULL        -- JSON payload (watcher-specific)
);

CREATE INDEX IF NOT EXISTS idx_ea56c63f_watcher_ts
    ON events_ea56c63f(watcher, timestamp);
```

### Merge Algorithm

On each `on_tick()` call:

```
1. Get last event for this watcher (ORDER BY timestamp DESC LIMIT 1)
2. If no last event → INSERT with duration = 0
3. Else:
   a. Compare data by merge key (full dict or specific keys)
   b. If data matches AND tick timestamp <= last.timestamp + last.duration + pulsetime:
        UPDATE last event's duration = max(last.duration, tick.ts - last.ts)
   c. Else:
        INSERT new event with duration = 0
```

This produces timeline sessions without storing redundant ticks.

| Watcher | PulseTime |
|---|---|
| `foreground` | 3s |
| `afk` | 10s |
| `power` | 120s |

### Storage growth

~110 events/day = ~40 KB/day = ~14 MB per year.

## Watcher Implementation Details

### ForegroundWatcher (composite)

Polls `GetForegroundWindow` + `GetWindowText` + `GetWindowThreadProcessId` + `psutil.Process().name()` every 2s. If process is a known browser, passes result through `BrowserAnalyzer` to extract page title and infer domain.

### AfkWatcher

Uses `GetLastInputInfo` with `GetTickCount64` wraparound-safe calculation every 5s. Status thresholds: `< 60s` = active, `60-300s` = idle, `> 300s` = away.

### PowerWatcher

Uses `psutil.sensors_battery()` every 60s. Returns `null` values on desktops without battery.

## Device Identity

- **Primary:** Machine GUID from `HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid`
- **Fallback:** Generated UUID4 stored in `%APPDATA%\TouchedGrassYet\device.json`

## Setup

```bash
uv run flet run           # desktop app
uv run flet run --web     # web app
```

## Dependencies

apsw, duckdb, flet, orjson, psutil, pywin32, rich

(Removed from initial scope: bleak, pycaw, pydantic, screeninfo, websockets, wmi)

## Sync (Planned)

Each device writes to its own `events_{id}` table. Sync copies remote tables as read-only replicas. No ID conflict — UUIDs and per-device table names are the namespace. `UNION ALL` across tables for cross-device timeline queries.

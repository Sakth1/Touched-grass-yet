# ADR-0002: Event-Sourced Collection Architecture

**Status:** Accepted (v0.4.1)

## Context

The exported Android datasets revealed architectural problems that incremental fixes cannot resolve:

- `duration=0` alongside `data.durations.duration_s=58` — two conflicting sources of truth in one row
- Multi-entity embedding — a single observation simultaneously represents current foreground app, per-package cumulative durations, and a provenance label
- The 58-second duration ceiling — `UsageStatsManager.queryUsageStats()` is a batch API that flushes approximately every 60s; reducing the poll interval does not change this
- AFK timeline contradictions — Android has no equivalent of Windows `GetLastInputInfo`; approximating idle time from app events produces fabricated precision
- Research confirms (Google Issue Tracker, April 2026) that even Digital Wellbeing uses privileged system APIs unavailable to third parties

## Decision

Replace the observation-centric pipeline with an **event-sourced architecture**.

### Core principles

1. **Platform APIs emit discrete events, not rows.** Each collector transforms a native API call into a typed, immutable, append-only event.

2. **Duration is never a first-class column.** Duration is computed from event timestamps during reconstruction, never stored at write time.

3. **Sessions are a derived view.** Reconstructed deterministically from events, not approximated via pulse-merge at write time.

4. **AFK is modeled as device state, not idle time.** On Android, only screen state and app-event gaps are observable. "Idle seconds" is fabricated precision.

5. **One entity per event.** No embedding of aggregated durations alongside point-in-time fields.

6. **Provenance is preserved.** Every event records which platform API produced it.

### Pipeline

```
Platform APIs
    │
    ▼
Raw Events (typed, immutable, append-only)
    │
    ├── foreground_transition    (app switch detected)
    ├── app_usage_interval       (per-package duration in window)
    ├── screen_state_change      (on↔off transition)
    ├── power_change             (battery snapshot)
    ├── idle_transition          (Windows only — precise)
    └── user_presence            (Android only — boolean approximation)
    │
    ▼
Canonical Event Store (raw_events table, SQLite)
    │
    ▼
Session Reconstructor (deterministic, idempotent)
    │
    ▼
Sessions Table (derived, recompute at will)
    │
    ▼
Device State Timeline (derived, contiguous blocks)
```

### Canonical entities

#### RawEvent (write-time entity)

```python
event_type: str       # "foreground_transition" | "app_usage_interval" | etc.
timestamp: float      # when the event occurred (UTC epoch)
collected_at: float   # when we observed it (UTC epoch)
payload: dict         # type-specific data
source: str           # which API produced this
device_id: str        # provenance
platform: str         # "windows" | "android"
```

#### Session (derived)

```python
start_ts: float       # first event timestamp
end_ts: float         # last event timestamp + poll_interval
duration_s: float     # sum of app_usage_interval durations OR end-start
app_key: str          # process name / package name
payload: dict         # merged metadata
session_type: str     # "foreground"
```

#### StateBlock (derived)

```python
start_ts: float
end_ts: float
state_type: str       # "screen_on" | "screen_off" | "charging" | "discharging"
value: any
```

### Migration

The migration happens in phases, maintaining backward compatibility at each step:

- **Phase A:** Add `raw_events` table + dual-write (events go to both old and new tables)
- **Phase B:** Rewrite Android collectors as event-driven
- **Phase C:** Rewrite sessionizer to consume raw_events
- **Phase D:** Remove legacy tables and pulse-merge code

## Consequences

- Positive: No more `duration=0` contradictions; one entity per event; deterministic session reconstruction; provenance tracking
- Positive: Android data becomes event-driven (fewer rows, higher semantic density); ~1440 rows/day → ~200
- Positive: AFK on Android no longer fabricates idle-seconds precision
- Neutral: Dual-write temporarily doubles storage writes during migration
- Negative: Windows precision cannot be matched on Android (fundamental API limitation — documented, not hidden)
- Migration effort: phased approach allows each step to be verified independently

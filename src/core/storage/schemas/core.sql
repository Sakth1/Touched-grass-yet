-- Schema v0.1
-- Shared device registry (platform-independent)

CREATE TABLE IF NOT EXISTS devices (
    device_id   TEXT PRIMARY KEY,
    hostname    TEXT,
    platform    TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT,
    is_current  INTEGER DEFAULT 0
);

-- Schema v0.4.1 — Canonical event store
-- Every platform API call produces typed, immutable, append-only events.
-- Duration is never stored — it is computed from event timestamps during reconstruction.

CREATE TABLE IF NOT EXISTS raw_events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id     TEXT NOT NULL,
    platform      TEXT NOT NULL,
    event_type    TEXT NOT NULL,          -- "foreground_transition" | "app_usage_interval" | etc.
    timestamp     REAL NOT NULL,          -- Unix epoch (UTC) — when the event occurred
    collected_at  REAL NOT NULL,          -- Unix epoch (UTC) — when we observed it
    tick_uuid     TEXT,                   -- UUID of the originating Tick (for traceability)
    payload       TEXT NOT NULL,          -- JSON payload, type-specific
    source        TEXT NOT NULL           -- API provenance (e.g., "usage_events", "getforegroundwindow")
);

CREATE INDEX IF NOT EXISTS idx_raw_events_type_ts
    ON raw_events(event_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_raw_events_device_ts
    ON raw_events(device_id, timestamp);

-- Schema v0.5 — Derived sessions (shared, not per-device)
-- Sessions are reconstructed from raw_events deterministically.

CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id     TEXT NOT NULL,
    platform      TEXT NOT NULL,
    start_ts      REAL NOT NULL,
    end_ts        REAL,
    duration_s    REAL,
    app_key       TEXT NOT NULL,
    payload       TEXT NOT NULL,
    session_type  TEXT DEFAULT 'foreground'
);

CREATE INDEX IF NOT EXISTS idx_sessions_device_app
    ON sessions(device_id, app_key, start_ts);

CREATE INDEX IF NOT EXISTS idx_sessions_ts
    ON sessions(device_id, start_ts);

-- Schema v0.6 — URL visit log (browser navigation events)

CREATE TABLE IF NOT EXISTS url_visits (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id        TEXT    NOT NULL,
    event_id         INTEGER REFERENCES raw_events(id),
    session_id       INTEGER REFERENCES sessions(id),

    url              TEXT    NOT NULL,
    scheme           TEXT,
    host             TEXT,
    domain           TEXT,
    path             TEXT,

    extraction_method TEXT,
    confidence        TEXT DEFAULT 'high',
    is_trackable      INTEGER DEFAULT 1,

    seen_at          REAL    NOT NULL,
    collected_at     REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_url_visits_device_seen
    ON url_visits(device_id, seen_at);

CREATE INDEX IF NOT EXISTS idx_url_visits_device_domain
    ON url_visits(device_id, domain, seen_at);

CREATE INDEX IF NOT EXISTS idx_url_visits_event
    ON url_visits(event_id);

CREATE INDEX IF NOT EXISTS idx_url_visits_session
    ON url_visits(session_id);

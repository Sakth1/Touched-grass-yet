-- Schema v0.1
-- Android event storage (one table per device)
-- Uses same events_{short_id} pattern as Windows
-- {short_id} is resolved at runtime by Storage.__init__()
--
-- data JSON payload:
--   {"package": "com.android.chrome",
--    "app_name": "Chrome",
--    "deltas": {"com.android.chrome": {"delta_ms": 60000, "delta_s": 60.0, "app_name": "Chrome"}},
--    "source": "delta"}
--
-- Events data (when source includes events):
--   {"events": [{"package": "...", "type": "resumed", "timestamp_ms": 1742169600000}, ...]}

CREATE TABLE IF NOT EXISTS events_{short_id} (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher    TEXT NOT NULL,
    timestamp  REAL NOT NULL,          -- Unix epoch seconds (UTC)
    duration   REAL DEFAULT 0,         -- seconds, rounded to 2 decimals
    data       TEXT NOT NULL           -- JSON payload
);

CREATE INDEX IF NOT EXISTS idx_{short_id}_watcher_ts
    ON events_{short_id}(watcher, timestamp);

-- Schema v0.2 — raw observations (no duration, no pulse-merge)

CREATE TABLE IF NOT EXISTS observations_{short_id} (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher    TEXT NOT NULL,
    timestamp  REAL NOT NULL,          -- Unix epoch seconds (UTC)
    data       TEXT NOT NULL,          -- JSON payload
    obs_type   TEXT DEFAULT 'snapshot' -- "snapshot" | "event" | "state"
);

CREATE INDEX IF NOT EXISTS idx_obs_{short_id}_watcher_ts
    ON observations_{short_id}(watcher, timestamp);

-- Schema v0.2 — computed foreground sessions

CREATE TABLE IF NOT EXISTS sessions_{short_id} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher     TEXT NOT NULL,          -- "foreground" | "android_foreground"
    start_ts    REAL NOT NULL,          -- Unix epoch, session start
    end_ts      REAL,                   -- Unix epoch, session end (NULL = ongoing)
    duration_s  REAL,                   -- Computed: end_ts - start_ts
    app_key     TEXT NOT NULL,          -- Process name / package name
    data        TEXT NOT NULL,          -- Aggregated metadata (JSON)
    source      TEXT                    -- "pulse" | "events" | "delta" | "stale"
);

CREATE INDEX IF NOT EXISTS idx_ses_{short_id}_app_ts
    ON sessions_{short_id}(app_key, start_ts);

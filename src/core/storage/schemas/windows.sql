-- Schema v0.1
-- Windows event storage (one table per device)
-- {short_id} is resolved at runtime by Storage.__init__()

CREATE TABLE IF NOT EXISTS events_{short_id} (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    watcher    TEXT NOT NULL,
    timestamp  REAL NOT NULL,          -- Unix epoch seconds (UTC)
    duration   REAL DEFAULT 0,         -- seconds, rounded to 2 decimals
    data       TEXT NOT NULL           -- JSON payload
);

CREATE INDEX IF NOT EXISTS idx_{short_id}_watcher_ts
    ON events_{short_id}(watcher, timestamp);

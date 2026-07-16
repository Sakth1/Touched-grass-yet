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

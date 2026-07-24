-- Schema v0.5 — legacy tables removed
-- {short_id} is resolved at runtime by Storage.__init__()
-- Legacy events_{short_id}, observations_{short_id}, sessions_{short_id}
-- are dropped during migration. Only raw_events and sessions remain.

DROP TABLE IF EXISTS events_{short_id};
DROP TABLE IF EXISTS observations_{short_id};
DROP TABLE IF EXISTS sessions_{short_id};

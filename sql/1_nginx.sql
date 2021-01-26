CREATE TABLE IF NOT EXISTS monitoring.nginx_logs
(
    id           SERIAL PRIMARY KEY NOT NULL,
    log          TEXT,
    infos        JSONB,
    file         TEXT,
    inserted_at  TIMESTAMP          NOT NULL default now(),
    processed_at TIMESTAMP,
    error        BOOLEAN            NOT NULL
);
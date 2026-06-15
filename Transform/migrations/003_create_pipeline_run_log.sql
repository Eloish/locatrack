CREATE SCHEMA IF NOT EXISTS pipeline;

CREATE TABLE IF NOT EXISTS pipeline.run_log (
    id          SERIAL PRIMARY KEY,
    source      VARCHAR(200) NOT NULL,
    status      VARCHAR(20)  NOT NULL CHECK (status IN ('running', 'success', 'error')),
    rows_loaded INTEGER,
    started_at  TIMESTAMP    NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMP,
    error_msg   TEXT
);

CREATE INDEX IF NOT EXISTS idx_run_log_source_status
    ON pipeline.run_log (source, status);

CREATE TABLE workers (
    id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    registered_at TEXT NOT NULL,
    last_heartbeat_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, id),
    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(id)) > 0)
);

CREATE INDEX idx_workers_liveness
    ON workers(workspace_id, last_heartbeat_at);
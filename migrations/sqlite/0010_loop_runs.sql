PRAGMA foreign_keys = ON;

CREATE TABLE loop_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    loop_id TEXT NOT NULL,
    input TEXT NOT NULL,
    status TEXT NOT NULL,
    state TEXT NOT NULL,
    next_action TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    token_revision INTEGER NOT NULL,
    loop_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id, loop_id)
        REFERENCES loops(workspace_id, id)
        ON DELETE RESTRICT,

    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(input)) > 0),
    CHECK (status IN ('in_progress', 'failed', 'completed', 'stopped')),
    CHECK (state = 'awaiting_snapshot'),
    CHECK (next_action = 'collect_snapshot'),
    CHECK (iteration > 0),
    CHECK (token_revision >= 0),
    CHECK (json_valid(loop_snapshot_json)),
    CHECK (length(trim(created_by)) > 0)
);

CREATE INDEX idx_loop_runs_lookup
    ON loop_runs(workspace_id, loop_id, created_at DESC);
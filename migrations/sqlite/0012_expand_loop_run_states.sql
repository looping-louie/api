PRAGMA foreign_keys = OFF;

ALTER TABLE loop_runs RENAME TO loop_runs_legacy;
ALTER TABLE loop_run_checkpoints RENAME TO loop_run_checkpoints_legacy;

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
    continuation_token TEXT,
    loop_snapshot_json TEXT NOT NULL,
    execution_context_json TEXT NOT NULL DEFAULT '{}',
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
    CHECK (state IN (
        'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
        'awaiting_commit', 'completed', 'failed'
    )),
    CHECK (next_action IN (
        'collect_snapshot', 'apply_operations', 'commit_if_allowed', 'none'
    )),
    CHECK (iteration > 0),
    CHECK (token_revision >= 0),
    CHECK (json_valid(loop_snapshot_json)),
    CHECK (json_valid(execution_context_json)),
    CHECK (length(trim(created_by)) > 0)
);

INSERT INTO loop_runs SELECT * FROM loop_runs_legacy;
DROP TABLE loop_runs_legacy;

CREATE TABLE loop_run_checkpoints (
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    token_revision INTEGER NOT NULL,
    continuation_token TEXT,
    state TEXT NOT NULL,
    next_action TEXT NOT NULL,
    context_json TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, run_id, token_revision),

    FOREIGN KEY (workspace_id, run_id)
        REFERENCES loop_runs(workspace_id, id)
        ON DELETE CASCADE,

    CHECK (token_revision >= 0),
    CHECK (state IN (
        'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
        'awaiting_commit', 'completed', 'failed'
    )),
    CHECK (next_action IN (
        'collect_snapshot', 'apply_operations', 'commit_if_allowed', 'none'
    )),
    CHECK (json_valid(context_json))
);

INSERT INTO loop_run_checkpoints SELECT * FROM loop_run_checkpoints_legacy;
DROP TABLE loop_run_checkpoints_legacy;

CREATE INDEX idx_loop_runs_lookup
    ON loop_runs(workspace_id, loop_id, created_at DESC);

PRAGMA foreign_keys = ON;
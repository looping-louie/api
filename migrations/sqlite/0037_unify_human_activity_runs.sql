PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

ALTER TABLE activity_run_checkpoints RENAME TO activity_run_checkpoints_legacy;
ALTER TABLE activity_runs RENAME TO activity_runs_legacy;

CREATE TABLE activity_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    input TEXT NOT NULL,
    status TEXT NOT NULL,
    state TEXT NOT NULL,
    next_action TEXT NOT NULL,
    iteration INTEGER NOT NULL,
    token_revision INTEGER NOT NULL,
    continuation_token TEXT,
    activity_snapshot_json TEXT NOT NULL,
    execution_context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id, activity_id)
        REFERENCES activities(workspace_id, id)
        ON DELETE RESTRICT,
    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(activity_id)) > 0),
    CHECK (length(trim(input)) > 0),
    CHECK (status IN ('in_progress', 'failed', 'completed', 'stopped')),
    CHECK (state IN (
        'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
        'awaiting_review_input', 'awaiting_commit',
        'awaiting_human_decision', 'completed', 'failed'
    )),
    CHECK (next_action IN (
        'collect_snapshot', 'apply_operations', 'submit_review_input',
        'commit_if_allowed', 'submit_human_decision', 'none'
    )),
    CHECK (iteration > 0),
    CHECK (token_revision >= 0),
    CHECK (json_valid(activity_snapshot_json)),
    CHECK (json_valid(execution_context_json)),
    CHECK (length(trim(created_by)) > 0)
);

INSERT INTO activity_runs
SELECT * FROM activity_runs_legacy;

CREATE TABLE activity_run_checkpoints (
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
        REFERENCES activity_runs(workspace_id, id)
        ON DELETE CASCADE,
    CHECK (token_revision >= 0),
    CHECK (state IN (
        'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
        'awaiting_review_input', 'awaiting_commit',
        'awaiting_human_decision', 'completed', 'failed'
    )),
    CHECK (next_action IN (
        'collect_snapshot', 'apply_operations', 'submit_review_input',
        'commit_if_allowed', 'submit_human_decision', 'none'
    )),
    CHECK (json_valid(context_json))
);

INSERT INTO activity_run_checkpoints
SELECT * FROM activity_run_checkpoints_legacy;

DROP TABLE activity_run_checkpoints_legacy;
DROP TABLE activity_runs_legacy;

CREATE INDEX idx_activity_runs_lookup
    ON activity_runs(workspace_id, activity_id, created_at DESC);

DROP TABLE pipeline_run_gates;

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;

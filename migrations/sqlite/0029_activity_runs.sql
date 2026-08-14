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
    CHECK (
        state IN (
            'awaiting_snapshot',
            'awaiting_generation',
            'awaiting_apply',
            'awaiting_review_input',
            'awaiting_commit',
            'completed',
            'failed'
        )
    ),
    CHECK (
        next_action IN (
            'collect_snapshot',
            'apply_operations',
            'submit_review_input',
            'commit_if_allowed',
            'none'
        )
    ),
    CHECK (iteration > 0),
    CHECK (token_revision >= 0),
    CHECK (json_valid(activity_snapshot_json)),
    CHECK (json_valid(execution_context_json)),
    CHECK (length(trim(created_by)) > 0)
);

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
    CHECK (
        state IN (
            'awaiting_snapshot',
            'awaiting_generation',
            'awaiting_apply',
            'awaiting_review_input',
            'awaiting_commit',
            'completed',
            'failed'
        )
    ),
    CHECK (
        next_action IN (
            'collect_snapshot',
            'apply_operations',
            'submit_review_input',
            'commit_if_allowed',
            'none'
        )
    ),
    CHECK (json_valid(context_json))
);

CREATE TABLE activity_run_idempotency (
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    token_revision INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, run_id, token_revision, idempotency_key),
    FOREIGN KEY (workspace_id, run_id)
        REFERENCES activity_runs(workspace_id, id)
        ON DELETE CASCADE,
    CHECK (token_revision >= 0),
    CHECK (length(trim(idempotency_key)) > 0),
    CHECK (json_valid(response_json))
);

INSERT INTO activity_runs (
    id, workspace_id, activity_id, input, status, state, next_action,
    iteration, token_revision, continuation_token, activity_snapshot_json,
    execution_context_json, created_at, created_by, updated_at
)
SELECT
    id, workspace_id, activity_id, input, status, state, next_action,
    iteration, token_revision, continuation_token, loop_snapshot_json,
    execution_context_json, created_at, created_by, updated_at
FROM loop_runs
WHERE activity_id IS NOT NULL;

INSERT INTO activity_run_checkpoints (
    workspace_id, run_id, token_revision, continuation_token, state,
    next_action, context_json, created_at
)
SELECT
    checkpoint.workspace_id, checkpoint.run_id, checkpoint.token_revision,
    checkpoint.continuation_token, checkpoint.state, checkpoint.next_action,
    checkpoint.context_json, checkpoint.created_at
FROM loop_run_checkpoints AS checkpoint
JOIN loop_runs AS run
    ON run.workspace_id = checkpoint.workspace_id
    AND run.id = checkpoint.run_id
WHERE run.activity_id IS NOT NULL;

INSERT INTO activity_run_idempotency (
    workspace_id, run_id, token_revision, idempotency_key, response_json,
    created_at
)
SELECT
    idempotency.workspace_id, idempotency.run_id, idempotency.token_revision,
    idempotency.idempotency_key, idempotency.response_json, idempotency.created_at
FROM loop_run_idempotency AS idempotency
JOIN loop_runs AS run
    ON run.workspace_id = idempotency.workspace_id
    AND run.id = idempotency.run_id
WHERE run.activity_id IS NOT NULL;

CREATE INDEX idx_activity_runs_lookup
    ON activity_runs(workspace_id, activity_id, created_at DESC);
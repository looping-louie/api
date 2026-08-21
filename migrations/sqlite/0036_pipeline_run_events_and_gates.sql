PRAGMA foreign_keys = OFF;

ALTER TABLE pipeline_run_steps RENAME TO pipeline_run_steps_legacy;
ALTER TABLE pipeline_runs RENAME TO pipeline_runs_legacy;

CREATE TABLE pipeline_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    input TEXT NOT NULL,
    commit_mode TEXT NOT NULL DEFAULT 'allow'
        CHECK (commit_mode IN ('allow', 'forbid')),
    status TEXT NOT NULL,
    worker_id TEXT,
    lease_token TEXT,
    lease_expires_at TEXT,
    attempt INTEGER NOT NULL DEFAULT 0,
    current_activity_run_id TEXT,
    pipeline_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id, pipeline_id)
        REFERENCES pipelines(workspace_id, id)
        ON DELETE RESTRICT,
    FOREIGN KEY (workspace_id, current_activity_run_id)
        REFERENCES activity_runs(workspace_id, id)
        ON DELETE RESTRICT,
    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(pipeline_id)) > 0),
    CHECK (length(trim(input)) > 0),
    CHECK (status IN (
        'queued', 'claimed', 'in_progress', 'waiting', 'failed', 'completed'
    )),
    CHECK (attempt >= 0),
    CHECK (json_valid(pipeline_snapshot_json)),
    CHECK (length(trim(created_by)) > 0)
);

INSERT INTO pipeline_runs (
    id, workspace_id, pipeline_id, input, commit_mode, status, worker_id,
    lease_token, lease_expires_at, attempt, current_activity_run_id,
    pipeline_snapshot_json, created_at, created_by, updated_at
)
SELECT
    id, workspace_id, pipeline_id, input, commit_mode, status, worker_id,
    lease_token, lease_expires_at, attempt, current_activity_run_id,
    pipeline_snapshot_json, created_at, created_by, updated_at
FROM pipeline_runs_legacy;

CREATE TABLE pipeline_run_steps (
    workspace_id TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    activity_id TEXT NOT NULL,
    status TEXT NOT NULL,
    activity_run_id TEXT,
    activity_snapshot_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, pipeline_run_id, position),
    FOREIGN KEY (workspace_id, pipeline_run_id)
        REFERENCES pipeline_runs(workspace_id, id)
        ON DELETE CASCADE,
    FOREIGN KEY (workspace_id, activity_run_id)
        REFERENCES activity_runs(workspace_id, id)
        ON DELETE RESTRICT,

    CHECK (position >= 0),
    CHECK (length(trim(activity_id)) > 0),
    CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
    CHECK (json_valid(activity_snapshot_json))
);

INSERT INTO pipeline_run_steps
SELECT * FROM pipeline_run_steps_legacy;

DROP TABLE pipeline_run_steps_legacy;
DROP TABLE pipeline_runs_legacy;

CREATE TABLE pipeline_run_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    activity_id TEXT,
    actor_id TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id, pipeline_run_id)
        REFERENCES pipeline_runs(workspace_id, id)
        ON DELETE CASCADE,

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(event_type)) > 0),
    CHECK (length(trim(actor_id)) > 0),
    CHECK (json_valid(payload_json))
);

CREATE TABLE pipeline_run_gates (
    workspace_id TEXT NOT NULL,
    pipeline_run_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    activity_id TEXT NOT NULL,
    status TEXT NOT NULL,
    comment TEXT,
    decided_by TEXT,
    decided_at TEXT,

    PRIMARY KEY (workspace_id, pipeline_run_id, position),
    FOREIGN KEY (workspace_id, pipeline_run_id)
        REFERENCES pipeline_runs(workspace_id, id)
        ON DELETE CASCADE,

    CHECK (position >= 0),
    CHECK (length(trim(activity_id)) > 0),
    CHECK (status IN ('pending', 'waiting', 'approved', 'rejected', 'cancelled')),
    CHECK (
        (status IN ('pending', 'waiting')
            AND comment IS NULL AND decided_by IS NULL AND decided_at IS NULL)
        OR (status IN ('approved', 'rejected', 'cancelled')
            AND decided_by IS NOT NULL AND decided_at IS NOT NULL)
    )
);

CREATE INDEX idx_pipeline_runs_lookup
    ON pipeline_runs(workspace_id, pipeline_id, created_at DESC);

CREATE INDEX idx_pipeline_runs_claim
    ON pipeline_runs(workspace_id, status, lease_expires_at, created_at);

CREATE INDEX idx_pipeline_run_steps_status
    ON pipeline_run_steps(workspace_id, pipeline_run_id, status, position);

CREATE INDEX idx_pipeline_run_events_lookup
    ON pipeline_run_events(workspace_id, pipeline_run_id, created_at ASC);

CREATE INDEX idx_pipeline_run_gates_lookup
    ON pipeline_run_gates(workspace_id, pipeline_run_id, activity_id);

PRAGMA foreign_keys = ON;
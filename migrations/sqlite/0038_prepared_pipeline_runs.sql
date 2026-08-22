PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

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
        'prepared', 'queued', 'claimed', 'in_progress', 'waiting', 'failed', 'completed'
    )),
    CHECK (attempt >= 0),
    CHECK (json_valid(pipeline_snapshot_json)),
    CHECK (length(trim(created_by)) > 0)
);

INSERT INTO pipeline_runs
SELECT * FROM pipeline_runs_legacy;

DROP TABLE pipeline_runs_legacy;

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;

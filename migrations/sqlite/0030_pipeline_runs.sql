CREATE TABLE pipeline_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    input TEXT NOT NULL,
    status TEXT NOT NULL,
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
    CHECK (status IN ('in_progress', 'failed', 'completed')),
    CHECK (json_valid(pipeline_snapshot_json)),
    CHECK (length(trim(created_by)) > 0)
);

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

CREATE INDEX idx_pipeline_runs_lookup
    ON pipeline_runs(workspace_id, pipeline_id, created_at DESC);

CREATE INDEX idx_pipeline_run_steps_status
    ON pipeline_run_steps(workspace_id, pipeline_run_id, status, position);
PRAGMA foreign_keys = OFF;

CREATE TABLE pipelines_replacement (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    harness_json TEXT,
    model_target_json TEXT,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (status IN ('active', 'disabled', 'archived')),
    CHECK (length(trim(created_by)) > 0),
    CHECK (length(trim(updated_by)) > 0),
    CHECK (harness_json IS NULL OR json_valid(harness_json)),
    CHECK (model_target_json IS NULL OR json_valid(model_target_json))
);

INSERT INTO pipelines_replacement (
    id, workspace_id, name, description, status, created_at, created_by,
    updated_at, updated_by, harness_json, model_target_json
)
SELECT
    id, workspace_id, name, description, status, created_at, created_by,
    updated_at, updated_by, harness_json, NULL
FROM pipelines;

DROP TABLE pipelines;
ALTER TABLE pipelines_replacement RENAME TO pipelines;

CREATE INDEX idx_pipelines_workspace_status_updated
    ON pipelines(workspace_id, status, updated_at DESC);

ALTER TABLE activities
    ADD COLUMN model_target_json TEXT
    CHECK (model_target_json IS NULL OR json_valid(model_target_json));

ALTER TABLE activities
    ADD COLUMN harness_json TEXT
    CHECK (harness_json IS NULL OR json_valid(harness_json));

PRAGMA foreign_keys = ON;

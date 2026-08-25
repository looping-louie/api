CREATE TABLE workspace_execution_defaults (
    workspace_id TEXT PRIMARY KEY,
    model_target_json TEXT,
    harness_json TEXT,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (model_target_json IS NULL OR json_valid(model_target_json)),
    CHECK (harness_json IS NULL OR json_valid(harness_json))
);

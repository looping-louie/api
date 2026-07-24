PRAGMA foreign_keys = ON;

CREATE TABLE pipelines (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(title)) > 0),
    CHECK (status IN ('active', 'disabled', 'archived')),
    CHECK (length(trim(created_by)) > 0),
    CHECK (length(trim(updated_by)) > 0)
);

CREATE TABLE pipeline_steps (
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    loop_id TEXT,
    gate_type TEXT,
    config_json TEXT,

    PRIMARY KEY (workspace_id, pipeline_id, position),

    FOREIGN KEY (workspace_id, pipeline_id)
        REFERENCES pipelines(workspace_id, id)
        ON DELETE CASCADE,

    FOREIGN KEY (workspace_id, loop_id)
        REFERENCES loops(workspace_id, id)
        ON DELETE RESTRICT,

    CHECK (position >= 0),
    CHECK (step_type IN ('loop', 'human_gate')),
    CHECK (gate_type IS NULL OR gate_type IN ('approval', 'quiz')),
    CHECK (config_json IS NULL OR json_valid(config_json)),
    CHECK (
        (
            step_type = 'loop'
            AND loop_id IS NOT NULL
            AND gate_type IS NULL
            AND config_json IS NULL
        )
        OR (
            step_type = 'human_gate'
            AND loop_id IS NULL
            AND (
                (gate_type = 'approval' AND config_json IS NULL)
                OR (gate_type = 'quiz' AND config_json IS NOT NULL)
            )
        )
    )
);

CREATE TABLE pipeline_changelog_entries (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    diff_json TEXT,
    content_json TEXT,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(pipeline_id)) > 0),
    CHECK (
        change_type IN (
            'created',
            'updated',
            'enabled',
            'disabled',
            'archived'
        )
    ),
    CHECK (length(trim(actor_id)) > 0),
    CHECK (diff_json IS NULL OR json_valid(diff_json)),
    CHECK (content_json IS NULL OR json_valid(content_json))
);

CREATE INDEX idx_pipelines_workspace_status_updated
    ON pipelines(workspace_id, status, updated_at DESC);

CREATE INDEX idx_pipeline_steps_loop
    ON pipeline_steps(workspace_id, loop_id);

CREATE INDEX idx_pipeline_changelog_lookup
    ON pipeline_changelog_entries(
        workspace_id,
        pipeline_id,
        changed_at DESC
    );

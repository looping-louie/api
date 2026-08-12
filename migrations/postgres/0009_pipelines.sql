CREATE TABLE pipelines (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,

    CONSTRAINT pipelines_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT pipelines_workspace_id_unique
        UNIQUE (workspace_id, id),

    CONSTRAINT pipelines_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT pipelines_title_not_empty
        CHECK (length(trim(title)) > 0),

    CONSTRAINT pipelines_status_valid
        CHECK (status IN ('active', 'disabled', 'archived')),

    CONSTRAINT pipelines_created_by_not_empty
        CHECK (length(trim(created_by)) > 0),

    CONSTRAINT pipelines_updated_by_not_empty
        CHECK (length(trim(updated_by)) > 0)
);

CREATE TABLE pipeline_steps (
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    step_type TEXT NOT NULL,
    loop_id TEXT,
    gate_type TEXT,
    config_json JSONB,

    PRIMARY KEY (workspace_id, pipeline_id, position),

    CONSTRAINT pipeline_steps_pipeline_fk
        FOREIGN KEY (workspace_id, pipeline_id)
        REFERENCES pipelines(workspace_id, id)
        ON DELETE CASCADE,

    CONSTRAINT pipeline_steps_loop_fk
        FOREIGN KEY (workspace_id, loop_id)
        REFERENCES loops(workspace_id, id)
        ON DELETE RESTRICT,

    CONSTRAINT pipeline_steps_position_valid
        CHECK (position >= 0),

    CONSTRAINT pipeline_steps_type_valid
        CHECK (step_type IN ('loop', 'human_gate')),

    CONSTRAINT pipeline_steps_gate_type_valid
        CHECK (gate_type IS NULL OR gate_type IN ('approval', 'quiz')),

    CONSTRAINT pipeline_steps_shape_valid
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
    changed_at TIMESTAMPTZ NOT NULL,
    diff_json JSONB,
    content_json JSONB,

    CONSTRAINT pipeline_changelog_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT pipeline_changelog_pipeline_id_not_empty
        CHECK (length(trim(pipeline_id)) > 0),

    CONSTRAINT pipeline_changelog_change_type_valid
        CHECK (
            change_type IN (
                'created',
                'updated',
                'enabled',
                'disabled',
                'archived'
            )
        ),

    CONSTRAINT pipeline_changelog_actor_not_empty
        CHECK (length(trim(actor_id)) > 0)
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

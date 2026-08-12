DROP TABLE pipeline_steps;

CREATE TABLE pipeline_steps (
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    activity_id TEXT NOT NULL,

    PRIMARY KEY (workspace_id, pipeline_id, position),

    FOREIGN KEY (workspace_id, pipeline_id)
        REFERENCES pipelines(workspace_id, id)
        ON DELETE CASCADE,

    FOREIGN KEY (workspace_id, activity_id)
        REFERENCES activities(workspace_id, id)
        ON DELETE RESTRICT,

    CHECK (position >= 0),
    CHECK (length(trim(activity_id)) > 0)
);

CREATE INDEX idx_pipeline_steps_activity
    ON pipeline_steps(workspace_id, activity_id);
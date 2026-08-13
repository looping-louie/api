CREATE TABLE pipeline_step_dependencies (
    workspace_id TEXT NOT NULL,
    pipeline_id TEXT NOT NULL,
    dependent_position INTEGER NOT NULL,
    dependency_activity_id TEXT NOT NULL,
    condition TEXT NOT NULL,

    PRIMARY KEY (
        workspace_id,
        pipeline_id,
        dependent_position,
        dependency_activity_id
    ),

    FOREIGN KEY (workspace_id, pipeline_id, dependent_position)
        REFERENCES pipeline_steps(workspace_id, pipeline_id, position)
        ON DELETE CASCADE,

    FOREIGN KEY (workspace_id, dependency_activity_id)
        REFERENCES activities(workspace_id, id)
        ON DELETE RESTRICT,

    CHECK (dependent_position >= 0),
    CHECK (length(trim(dependency_activity_id)) > 0),
    CHECK (condition IN ('succeed', 'failure'))
);

CREATE INDEX idx_pipeline_step_dependencies_activity
    ON pipeline_step_dependencies(workspace_id, dependency_activity_id);
PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

ALTER TABLE pipeline_step_dependencies RENAME TO pipeline_step_dependencies_legacy;
ALTER TABLE pipeline_steps RENAME TO pipeline_steps_legacy;
ALTER TABLE pipeline_run_events RENAME TO pipeline_run_events_legacy;
ALTER TABLE pipeline_run_steps RENAME TO pipeline_run_steps_legacy;
ALTER TABLE pipeline_runs RENAME TO pipeline_runs_legacy;
ALTER TABLE pipeline_changelog_entries RENAME TO pipeline_changelog_entries_legacy;
ALTER TABLE pipelines RENAME TO pipelines_legacy;

CREATE TABLE pipelines (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    harness_json TEXT,
    model_target_json TEXT,
    model_id TEXT,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,
    UNIQUE (user_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (status IN ('active', 'disabled', 'archived')),
    CHECK (harness_json IS NULL OR json_valid(harness_json)),
    CHECK (model_target_json IS NULL OR json_valid(model_target_json)),
    CHECK (length(trim(created_by)) > 0),
    CHECK (length(trim(updated_by)) > 0)
);

INSERT INTO pipelines (
    id, user_id, name, description, status, harness_json, model_target_json,
    model_id, created_at, created_by, updated_at, updated_by
)
SELECT
    legacy.id,
    (
        SELECT membership.user_id
        FROM workspace_memberships AS membership
        WHERE membership.workspace_id = legacy.workspace_id
          AND membership.role = 'owner'
        ORDER BY membership.created_at ASC, membership.user_id ASC
        LIMIT 1
    ),
    legacy.name, legacy.description, legacy.status, legacy.harness_json,
    legacy.model_target_json, legacy.model_id, legacy.created_at,
    legacy.created_by, legacy.updated_at, legacy.updated_by
FROM pipelines_legacy AS legacy;

CREATE TABLE pipeline_changelog_entries (
    id TEXT PRIMARY KEY,
    pipeline_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    diff_json TEXT,
    content_json TEXT,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE RESTRICT,

    CHECK (length(trim(pipeline_id)) > 0),
    CHECK (change_type IN ('created', 'updated', 'enabled', 'disabled', 'archived')),
    CHECK (length(trim(actor_id)) > 0),
    CHECK (diff_json IS NULL OR json_valid(diff_json)),
    CHECK (content_json IS NULL OR json_valid(content_json))
);

INSERT INTO pipeline_changelog_entries (
    id, pipeline_id, user_id, change_type, actor_id, changed_at, diff_json, content_json
)
SELECT
    legacy.id, legacy.pipeline_id, pipeline.user_id, legacy.change_type,
    legacy.actor_id, legacy.changed_at, legacy.diff_json, legacy.content_json
FROM pipeline_changelog_entries_legacy AS legacy
JOIN pipelines AS pipeline ON pipeline.id = legacy.pipeline_id;

CREATE TABLE pipeline_steps (
    pipeline_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    activity_id TEXT NOT NULL,

    PRIMARY KEY (pipeline_id, position),
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE,

    CHECK (position >= 0),
    CHECK (length(trim(activity_id)) > 0)
);

INSERT INTO pipeline_steps (pipeline_id, position, activity_id)
SELECT pipeline_id, position, activity_id
FROM pipeline_steps_legacy;

CREATE TABLE pipeline_step_dependencies (
    pipeline_id TEXT NOT NULL,
    dependent_position INTEGER NOT NULL,
    dependency_activity_id TEXT NOT NULL,
    condition TEXT NOT NULL,

    PRIMARY KEY (pipeline_id, dependent_position, dependency_activity_id),
    FOREIGN KEY (pipeline_id, dependent_position)
        REFERENCES pipeline_steps(pipeline_id, position)
        ON DELETE CASCADE,

    CHECK (dependent_position >= 0),
    CHECK (length(trim(dependency_activity_id)) > 0),
    CHECK (condition IN ('success', 'failure'))
);

INSERT INTO pipeline_step_dependencies (
    pipeline_id, dependent_position, dependency_activity_id, condition
)
SELECT pipeline_id, dependent_position, dependency_activity_id, condition
FROM pipeline_step_dependencies_legacy;

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

    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE RESTRICT,
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE RESTRICT,
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

INSERT INTO pipeline_run_events
SELECT * FROM pipeline_run_events_legacy;

DROP TABLE pipeline_run_events_legacy;
DROP TABLE pipeline_run_steps_legacy;
DROP TABLE pipeline_runs_legacy;
DROP TABLE pipeline_step_dependencies_legacy;
DROP TABLE pipeline_steps_legacy;
DROP TABLE pipeline_changelog_entries_legacy;
DROP TABLE pipelines_legacy;

CREATE INDEX idx_pipelines_user_status_updated
    ON pipelines(user_id, status, updated_at DESC);
CREATE INDEX idx_pipeline_changelog_lookup
    ON pipeline_changelog_entries(user_id, pipeline_id, changed_at DESC);
CREATE INDEX idx_pipeline_steps_activity
    ON pipeline_steps(activity_id);
CREATE INDEX idx_pipeline_step_dependencies_activity
    ON pipeline_step_dependencies(dependency_activity_id);
CREATE INDEX idx_pipeline_runs_lookup
    ON pipeline_runs(workspace_id, pipeline_id, created_at DESC);
CREATE INDEX idx_pipeline_runs_claim
    ON pipeline_runs(workspace_id, status, lease_expires_at, created_at);
CREATE INDEX idx_pipeline_run_steps_status
    ON pipeline_run_steps(workspace_id, pipeline_run_id, status, position);
CREATE INDEX idx_pipeline_run_events_lookup
    ON pipeline_run_events(workspace_id, pipeline_run_id, created_at ASC);

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;
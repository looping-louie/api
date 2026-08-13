CREATE TABLE activities (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    config_json TEXT NOT NULL,
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
    CHECK (activity_type IN ('loop', 'human_gate')),
    CHECK (json_valid(config_json)),
    CHECK (length(trim(created_by)) > 0),
    CHECK (length(trim(updated_by)) > 0)
);

CREATE TABLE activity_changelog_entries (
    id TEXT PRIMARY KEY,
    activity_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    diff_json TEXT,
    content_json TEXT,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(activity_id)) > 0),
    CHECK (
        change_type IN (
            'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
        )
    ),
    CHECK (length(trim(actor_id)) > 0),
    CHECK (diff_json IS NULL OR json_valid(diff_json)),
    CHECK (content_json IS NULL OR json_valid(content_json))
);

CREATE INDEX idx_activities_workspace_updated
    ON activities(workspace_id, updated_at DESC);

CREATE INDEX idx_activity_changelog_lookup
    ON activity_changelog_entries(workspace_id, activity_id, changed_at DESC);

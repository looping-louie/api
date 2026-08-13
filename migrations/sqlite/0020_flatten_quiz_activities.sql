PRAGMA foreign_keys = OFF;

INSERT OR IGNORE INTO activity_changelog_entries (
    id,
    activity_id,
    workspace_id,
    change_type,
    actor_id,
    changed_at,
    diff_json,
    content_json
)
SELECT
    'migration:0020:quiz:' || hex(id),
    id,
    workspace_id,
    'updated',
    'system:migration:0020',
    strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    json_object(
        'type', json_object('from', 'human_gate', 'to', 'quiz'),
        'config', json_object(
            'from', json(config_json),
            'to', json_object(
                'type', 'quiz',
                'quiz', json_extract(config_json, '$.quiz')
            )
        )
    ),
    NULL
FROM activities
WHERE activity_type = 'human_gate'
    AND json_extract(config_json, '$.gate_type') = 'quiz';

CREATE TABLE activities_replacement (
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
    CHECK (activity_type IN ('approval', 'quiz', 'loop')),
    CHECK (json_valid(config_json)),
    CHECK (length(trim(created_by)) > 0),
    CHECK (length(trim(updated_by)) > 0)
);

INSERT INTO activities_replacement (
    id,
    workspace_id,
    title,
    description,
    status,
    activity_type,
    config_json,
    created_at,
    created_by,
    updated_at,
    updated_by
)
SELECT
    id,
    workspace_id,
    title,
    description,
    status,
    CASE
        WHEN activity_type = 'human_gate'
            AND json_extract(config_json, '$.gate_type') = 'quiz'
        THEN 'quiz'
        ELSE activity_type
    END,
    CASE
        WHEN activity_type = 'human_gate'
            AND json_extract(config_json, '$.gate_type') = 'quiz'
        THEN json_object(
            'type', 'quiz',
            'quiz', json_extract(config_json, '$.quiz')
        )
        ELSE config_json
    END,
    created_at,
    created_by,
    updated_at,
    updated_by
FROM activities;

DROP TABLE activities;
ALTER TABLE activities_replacement RENAME TO activities;

CREATE INDEX idx_activities_workspace_updated
    ON activities(workspace_id, updated_at DESC);

PRAGMA foreign_keys = ON;

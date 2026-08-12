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
    'migration:0018:archive:' || hex(activity.workspace_id) || ':' || hex(activity.id),
    activity.id,
    activity.workspace_id,
    'archived',
    'system:migration:0018',
    strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    json_object('status', json_object('from', activity.status, 'to', 'archived')),
    json_object('status', 'archived')
FROM activities AS activity
INNER JOIN activity_catalog_installations AS installation
    ON installation.workspace_id = activity.workspace_id
    AND installation.activity_id = activity.id
WHERE activity.status <> 'archived';

UPDATE activities AS activity
SET
    status = 'archived',
    updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
    updated_by = 'system:migration:0018'
WHERE activity.status <> 'archived'
    AND EXISTS (
        SELECT 1
        FROM activity_catalog_installations AS installation
        WHERE installation.workspace_id = activity.workspace_id
            AND installation.activity_id = activity.id
    );

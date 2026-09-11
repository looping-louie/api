UPDATE users
SET settings_json = json_set(
    settings_json,
    '$.default_model_id',
    (
        SELECT defaults.model_id
        FROM workspace_execution_defaults AS defaults
        JOIN workspace_memberships AS membership
            ON membership.workspace_id = defaults.workspace_id
        WHERE membership.user_id = users.id
        ORDER BY membership.is_default DESC, membership.created_at ASC, membership.workspace_id ASC
        LIMIT 1
    )
);

UPDATE users
SET settings_json = json_set(
    settings_json,
    '$.default_harness',
    COALESCE(
        (
            SELECT json(defaults.harness_json)
            FROM workspace_execution_defaults AS defaults
            JOIN workspace_memberships AS membership
                ON membership.workspace_id = defaults.workspace_id
            WHERE membership.user_id = users.id
            ORDER BY membership.is_default DESC, membership.created_at ASC, membership.workspace_id ASC
            LIMIT 1
        ),
        json_extract(settings_json, '$.default_harness')
    )
)
WHERE json_extract(settings_json, '$.default_harness') IS NULL;

DROP TABLE workspace_execution_defaults;

UPDATE activities
SET config_json = json_remove(config_json, '$.type')
WHERE json_type(config_json, '$.type') IS NOT NULL;

UPDATE activity_changelog_entries
SET content_json = json_remove(content_json, '$.config.type')
WHERE content_json IS NOT NULL;

UPDATE activity_changelog_entries
SET diff_json = json_remove(
    diff_json,
    '$.config.type',
    '$.config.from.type',
    '$.config.to.type'
)
WHERE diff_json IS NOT NULL;

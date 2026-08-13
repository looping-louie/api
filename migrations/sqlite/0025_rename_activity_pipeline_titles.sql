ALTER TABLE activities RENAME COLUMN title TO name;
ALTER TABLE pipelines RENAME COLUMN title TO name;

UPDATE activity_changelog_entries
SET diff_json = json_set(
    json_remove(diff_json, '$.title'),
    '$.name',
    json_extract(diff_json, '$.title')
)
WHERE json_type(diff_json, '$.title') IS NOT NULL;

UPDATE activity_changelog_entries
SET content_json = json_set(
    json_remove(content_json, '$.title'),
    '$.name',
    json_extract(content_json, '$.title')
)
WHERE json_type(content_json, '$.title') IS NOT NULL;

UPDATE pipeline_changelog_entries
SET diff_json = json_set(
    json_remove(diff_json, '$.title'),
    '$.name',
    json_extract(diff_json, '$.title')
)
WHERE json_type(diff_json, '$.title') IS NOT NULL;

UPDATE pipeline_changelog_entries
SET content_json = json_set(
    json_remove(content_json, '$.title'),
    '$.name',
    json_extract(content_json, '$.title')
)
WHERE json_type(content_json, '$.title') IS NOT NULL;

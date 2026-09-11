ALTER TABLE activities ADD COLUMN model_id TEXT;
ALTER TABLE pipelines ADD COLUMN model_id TEXT;
ALTER TABLE workspace_execution_defaults ADD COLUMN model_id TEXT;

UPDATE activities
SET
    model_id = json_extract(model_target_json, '$.model_id'),
    config_json = CASE
        WHEN json_type(config_json, '$.agents') = 'array' THEN
            json_set(
                config_json,
                '$.agents',
                (
                    SELECT json_group_array(
                        CASE
                            WHEN json_type(agent.value, '$.model_target.model_id') = 'text'
                            THEN json_remove(
                                json_set(
                                    agent.value,
                                    '$.model_id',
                                    json_extract(agent.value, '$.model_target.model_id')
                                ),
                                '$.model_target'
                            )
                            ELSE agent.value
                        END
                    )
                    FROM json_each(config_json, '$.agents') AS agent
                )
            )
        ELSE config_json
    END;

UPDATE pipelines
SET model_id = json_extract(model_target_json, '$.model_id');

UPDATE workspace_execution_defaults
SET model_id = json_extract(model_target_json, '$.model_id');
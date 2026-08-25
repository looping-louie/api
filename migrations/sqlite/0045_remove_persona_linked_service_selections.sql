UPDATE activities AS activity
SET config_json = json_set(
	activity.config_json,
	'$.agents',
	json(
		(
			SELECT json_group_array(
				CASE
					WHEN selection.persona_id IS NOT NULL
						AND json_extract(agent.value, '$.model_target') IS NULL
					THEN json_set(
						json_remove(agent.value, '$.model_id'),
						'$.model_target',
						json_object(
							'linked_service_id', selection.linked_service_id,
							'model_id', selection.model_id
						)
					)
					ELSE json_remove(agent.value, '$.model_id')
				END
			)
			FROM json_each(activity.config_json, '$.agents') AS agent
			LEFT JOIN persona_linked_service_selections AS selection
				ON selection.workspace_id = activity.workspace_id
				AND selection.persona_id = json_extract(agent.value, '$.persona_id')
		)
	)
)
WHERE json_type(activity.config_json, '$.agents') = 'array';

DROP TABLE persona_linked_service_selections;

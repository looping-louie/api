PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

ALTER TABLE pipeline_step_dependencies RENAME TO pipeline_step_dependencies_legacy;
ALTER TABLE pipeline_steps RENAME TO pipeline_steps_legacy;
ALTER TABLE activity_run_checkpoints RENAME TO activity_run_checkpoints_legacy;
ALTER TABLE activity_runs RENAME TO activity_runs_legacy;
ALTER TABLE activity_changelog_entries RENAME TO activity_changelog_entries_legacy;
ALTER TABLE activities RENAME TO activities_legacy;

CREATE TABLE activities (
	id TEXT PRIMARY KEY,
	user_id TEXT NOT NULL,
	workspace_id TEXT,
	name TEXT NOT NULL,
	description TEXT NOT NULL,
	status TEXT NOT NULL,
	activity_type TEXT NOT NULL,
	config_json TEXT NOT NULL,
	model_target_json TEXT,
	harness_json TEXT,
	model_id TEXT,
	created_at TEXT NOT NULL,
	created_by TEXT NOT NULL,
	updated_at TEXT NOT NULL,
	updated_by TEXT NOT NULL,

	FOREIGN KEY (user_id)
		REFERENCES users(id)
		ON DELETE RESTRICT,
	FOREIGN KEY (workspace_id)
		REFERENCES workspaces(id)
		ON DELETE SET NULL,

	UNIQUE (user_id, id),

	CHECK (length(trim(id)) > 0),
	CHECK (length(trim(name)) > 0),
	CHECK (status IN ('active', 'disabled', 'archived')),
	CHECK (activity_type IN (
		'approval', 'quiz', 'direct_loop', 'refinement_loop',
		'roundtable_loop'
	)),
	CHECK (json_valid(config_json)),
	CHECK (model_target_json IS NULL OR json_valid(model_target_json)),
	CHECK (harness_json IS NULL OR json_valid(harness_json)),
	CHECK (length(trim(created_by)) > 0),
	CHECK (length(trim(updated_by)) > 0)
);

INSERT INTO activities (
	id, user_id, workspace_id, name, description, status, activity_type,
	config_json, model_target_json, harness_json, model_id, created_at,
	created_by, updated_at, updated_by
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
	legacy.workspace_id,
	legacy.name,
	legacy.description,
	legacy.status,
	legacy.activity_type,
	legacy.config_json,
	legacy.model_target_json,
	legacy.harness_json,
	legacy.model_id,
	legacy.created_at,
	legacy.created_by,
	legacy.updated_at,
	legacy.updated_by
FROM activities_legacy AS legacy;

CREATE TABLE activity_changelog_entries (
	id TEXT PRIMARY KEY,
	activity_id TEXT NOT NULL,
	user_id TEXT NOT NULL,
	workspace_id TEXT,
	change_type TEXT NOT NULL,
	actor_id TEXT NOT NULL,
	changed_at TEXT NOT NULL,
	diff_json TEXT,
	content_json TEXT,

	FOREIGN KEY (user_id)
		REFERENCES users(id)
		ON DELETE RESTRICT,
	FOREIGN KEY (workspace_id)
		REFERENCES workspaces(id)
		ON DELETE SET NULL,

	CHECK (length(trim(activity_id)) > 0),
	CHECK (change_type IN (
		'created', 'updated', 'enabled', 'disabled', 'archived', 'deleted'
	)),
	CHECK (length(trim(actor_id)) > 0),
	CHECK (diff_json IS NULL OR json_valid(diff_json)),
	CHECK (content_json IS NULL OR json_valid(content_json))
);

INSERT INTO activity_changelog_entries (
	id, activity_id, user_id, workspace_id, change_type, actor_id, changed_at,
	diff_json, content_json
)
SELECT
	legacy.id,
	legacy.activity_id,
	activity.user_id,
	legacy.workspace_id,
	legacy.change_type,
	legacy.actor_id,
	legacy.changed_at,
	legacy.diff_json,
	legacy.content_json
FROM activity_changelog_entries_legacy AS legacy
JOIN activities AS activity ON activity.id = legacy.activity_id;

CREATE TABLE pipeline_steps (
	workspace_id TEXT NOT NULL,
	pipeline_id TEXT NOT NULL,
	position INTEGER NOT NULL,
	activity_id TEXT NOT NULL,

	PRIMARY KEY (workspace_id, pipeline_id, position),
	FOREIGN KEY (workspace_id, pipeline_id)
		REFERENCES pipelines(workspace_id, id)
		ON DELETE CASCADE,

	CHECK (position >= 0),
	CHECK (length(trim(activity_id)) > 0)
);

INSERT INTO pipeline_steps
SELECT * FROM pipeline_steps_legacy;

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

	CHECK (dependent_position >= 0),
	CHECK (length(trim(dependency_activity_id)) > 0),
	CHECK (condition IN ('success', 'failure'))
);

INSERT INTO pipeline_step_dependencies
SELECT * FROM pipeline_step_dependencies_legacy;

CREATE TABLE activity_runs (
	id TEXT PRIMARY KEY,
	workspace_id TEXT NOT NULL,
	activity_id TEXT NOT NULL,
	input TEXT NOT NULL,
	status TEXT NOT NULL,
	state TEXT NOT NULL,
	next_action TEXT NOT NULL,
	iteration INTEGER NOT NULL,
	token_revision INTEGER NOT NULL,
	continuation_token TEXT,
	activity_snapshot_json TEXT NOT NULL,
	execution_context_json TEXT NOT NULL DEFAULT '{}',
	created_at TEXT NOT NULL,
	created_by TEXT NOT NULL,
	updated_at TEXT NOT NULL,

	UNIQUE (workspace_id, id),

	CHECK (length(trim(id)) > 0),
	CHECK (length(trim(activity_id)) > 0),
	CHECK (length(trim(input)) > 0),
	CHECK (status IN ('in_progress', 'failed', 'completed', 'stopped')),
	CHECK (state IN (
		'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
		'awaiting_review_input', 'awaiting_commit',
		'awaiting_human_decision', 'completed', 'failed'
	)),
	CHECK (next_action IN (
		'collect_snapshot', 'apply_operations', 'submit_review_input',
		'commit_if_allowed', 'submit_human_decision', 'none'
	)),
	CHECK (iteration > 0),
	CHECK (token_revision >= 0),
	CHECK (json_valid(activity_snapshot_json)),
	CHECK (json_valid(execution_context_json)),
	CHECK (length(trim(created_by)) > 0)
);

INSERT INTO activity_runs
SELECT * FROM activity_runs_legacy;

CREATE TABLE activity_run_checkpoints (
	workspace_id TEXT NOT NULL,
	run_id TEXT NOT NULL,
	token_revision INTEGER NOT NULL,
	continuation_token TEXT,
	state TEXT NOT NULL,
	next_action TEXT NOT NULL,
	context_json TEXT NOT NULL,
	created_at TEXT NOT NULL,

	PRIMARY KEY (workspace_id, run_id, token_revision),
	FOREIGN KEY (workspace_id, run_id)
		REFERENCES activity_runs(workspace_id, id)
		ON DELETE CASCADE,
	CHECK (token_revision >= 0),
	CHECK (state IN (
		'awaiting_snapshot', 'awaiting_generation', 'awaiting_apply',
		'awaiting_review_input', 'awaiting_commit',
		'awaiting_human_decision', 'completed', 'failed'
	)),
	CHECK (next_action IN (
		'collect_snapshot', 'apply_operations', 'submit_review_input',
		'commit_if_allowed', 'submit_human_decision', 'none'
	)),
	CHECK (json_valid(context_json))
);

INSERT INTO activity_run_checkpoints
SELECT * FROM activity_run_checkpoints_legacy;

DROP TABLE pipeline_step_dependencies_legacy;
DROP TABLE pipeline_steps_legacy;
DROP TABLE activity_run_checkpoints_legacy;
DROP TABLE activity_runs_legacy;
DROP TABLE activity_changelog_entries_legacy;
DROP TABLE activities_legacy;

CREATE INDEX idx_activities_user_updated
	ON activities(user_id, updated_at DESC);
CREATE INDEX idx_activities_workspace_updated
	ON activities(workspace_id, updated_at DESC);
CREATE INDEX idx_activity_changelog_lookup
	ON activity_changelog_entries(user_id, activity_id, changed_at DESC);
CREATE INDEX idx_pipeline_steps_activity
	ON pipeline_steps(workspace_id, activity_id);
CREATE INDEX idx_pipeline_step_dependencies_activity
	ON pipeline_step_dependencies(workspace_id, dependency_activity_id);
CREATE INDEX idx_activity_runs_lookup
	ON activity_runs(workspace_id, activity_id, created_at DESC);

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;

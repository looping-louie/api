ALTER TABLE workspaces RENAME TO projects;
ALTER TABLE workspace_memberships RENAME TO project_memberships;
ALTER TABLE workspace_instruction_settings RENAME TO project_instruction_settings;

ALTER TABLE activities RENAME COLUMN workspace_id TO project_id;
ALTER TABLE activity_catalog_installations RENAME COLUMN workspace_id TO project_id;
ALTER TABLE activity_changelog_entries RENAME COLUMN workspace_id TO project_id;
ALTER TABLE activity_run_checkpoints RENAME COLUMN workspace_id TO project_id;
ALTER TABLE activity_run_idempotency RENAME COLUMN workspace_id TO project_id;
ALTER TABLE activity_runs RENAME COLUMN workspace_id TO project_id;
ALTER TABLE instructions RENAME COLUMN owner_workspace_id TO owner_project_id;
ALTER TABLE pipeline_run_events RENAME COLUMN workspace_id TO project_id;
ALTER TABLE pipeline_run_steps RENAME COLUMN workspace_id TO project_id;
ALTER TABLE pipeline_runs RENAME COLUMN workspace_id TO project_id;
ALTER TABLE workers RENAME COLUMN workspace_id TO project_id;
ALTER TABLE project_instruction_settings RENAME COLUMN workspace_id TO project_id;
ALTER TABLE project_memberships RENAME COLUMN workspace_id TO project_id;

DROP INDEX idx_activities_workspace_updated;
DROP INDEX idx_activity_runs_lookup;
DROP INDEX idx_pipeline_run_events_lookup;
DROP INDEX idx_pipeline_run_steps_status;
DROP INDEX idx_pipeline_runs_claim;
DROP INDEX idx_pipeline_runs_lookup;
DROP INDEX idx_workers_liveness;
DROP INDEX idx_workspace_instruction_settings_enabled;
DROP INDEX idx_workspace_memberships_default;
DROP INDEX idx_workspace_memberships_user;

CREATE INDEX idx_activities_project_updated
    ON activities(project_id, updated_at DESC);
CREATE INDEX idx_activity_runs_lookup
    ON activity_runs(project_id, activity_id, created_at DESC);
CREATE INDEX idx_pipeline_run_events_lookup
    ON pipeline_run_events(project_id, pipeline_run_id, created_at ASC);
CREATE INDEX idx_pipeline_run_steps_status
    ON pipeline_run_steps(project_id, pipeline_run_id, status, position);
CREATE INDEX idx_pipeline_runs_claim
    ON pipeline_runs(project_id, status, lease_expires_at, created_at);
CREATE INDEX idx_pipeline_runs_lookup
    ON pipeline_runs(project_id, pipeline_id, created_at DESC);
CREATE INDEX idx_workers_liveness
    ON workers(project_id, last_heartbeat_at);
CREATE INDEX idx_project_instruction_settings_enabled
    ON project_instruction_settings(project_id, enabled);
CREATE UNIQUE INDEX idx_project_memberships_default
    ON project_memberships(user_id)
    WHERE is_default = 1;
CREATE INDEX idx_project_memberships_user
    ON project_memberships(user_id);
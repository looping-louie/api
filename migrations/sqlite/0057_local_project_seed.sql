PRAGMA foreign_keys = OFF;

UPDATE activities
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE activity_catalog_installations
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE activity_changelog_entries
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE activity_run_checkpoints
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE activity_run_idempotency
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE activity_runs
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE instructions
SET owner_project_id = 'local-project'
WHERE owner_project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE pipeline_run_events
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE pipeline_run_steps
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE pipeline_runs
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE workers
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE project_instruction_settings
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE project_memberships
SET project_id = 'local-project'
WHERE project_id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');

UPDATE projects
SET id = 'local-project', name = 'Local project'
WHERE id = 'local-workspace'
  AND NOT EXISTS (SELECT 1 FROM projects WHERE id = 'local-project');
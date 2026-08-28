ALTER TABLE workspaces RENAME TO projects;
ALTER TABLE workspace_memberships RENAME TO project_memberships;
ALTER TABLE workspace_instruction_settings RENAME TO project_instruction_settings;

ALTER TABLE instructions RENAME COLUMN owner_workspace_id TO owner_project_id;
ALTER TABLE provider_credentials RENAME COLUMN workspace_id TO project_id;
ALTER TABLE loop_catalog_installations RENAME COLUMN workspace_id TO project_id;
ALTER TABLE loops RENAME COLUMN workspace_id TO project_id;
ALTER TABLE loop_agents RENAME COLUMN workspace_id TO project_id;
ALTER TABLE loop_changelog_entries RENAME COLUMN workspace_id TO project_id;
ALTER TABLE pipelines RENAME COLUMN workspace_id TO project_id;
ALTER TABLE pipeline_steps RENAME COLUMN workspace_id TO project_id;
ALTER TABLE pipeline_changelog_entries RENAME COLUMN workspace_id TO project_id;
ALTER TABLE project_instruction_settings RENAME COLUMN workspace_id TO project_id;
ALTER TABLE project_memberships RENAME COLUMN workspace_id TO project_id;
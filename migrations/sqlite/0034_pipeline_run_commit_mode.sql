ALTER TABLE pipeline_runs
    ADD COLUMN commit_mode TEXT NOT NULL DEFAULT 'allow'
    CHECK (commit_mode IN ('allow', 'forbid'));
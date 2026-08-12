PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS workspace_memberships (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    is_default INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, user_id),

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(user_id)) > 0),
    CHECK (role IN ('owner', 'admin', 'member')),
    CHECK (is_default IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user
    ON workspace_memberships(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_memberships_default
    ON workspace_memberships(user_id)
    WHERE is_default = 1;

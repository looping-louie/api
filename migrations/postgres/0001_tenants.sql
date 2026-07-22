CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    checksum TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT workspaces_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT workspaces_name_not_empty
        CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS workspace_memberships (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        workspace_id,
        user_id
    ),

    CONSTRAINT workspace_memberships_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT workspace_memberships_user_not_empty
        CHECK (length(trim(user_id)) > 0),

    CONSTRAINT workspace_memberships_role_valid
        CHECK (role IN ('owner', 'admin', 'member'))
);

CREATE INDEX IF NOT EXISTS idx_workspace_memberships_user
    ON workspace_memberships(user_id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_workspace_memberships_default
    ON workspace_memberships(user_id)
    WHERE is_default = TRUE;

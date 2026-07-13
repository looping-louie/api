PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS provider_credentials (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 0,
    enabled_by TEXT,
    enabled_on TEXT,
    key_trimmed TEXT,
    key_ciphertext TEXT,
    key_version INTEGER NOT NULL DEFAULT 1,
    base_url TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (
        workspace_id,
        provider
    ),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(provider)) > 0),
    CHECK (enabled IN (0, 1)),
    CHECK (key_version >= 1)
);

CREATE INDEX IF NOT EXISTS idx_provider_credentials_workspace
    ON provider_credentials(workspace_id);

CREATE INDEX IF NOT EXISTS idx_provider_credentials_enabled
    ON provider_credentials(
        workspace_id,
        enabled
    );

CREATE TABLE IF NOT EXISTS provider_credentials (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    enabled_by TEXT,
    enabled_on TIMESTAMPTZ,
    key_trimmed TEXT,
    key_ciphertext TEXT,
    key_version INTEGER NOT NULL DEFAULT 1,
    base_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT provider_credentials_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT provider_credentials_workspace_provider_unique
        UNIQUE (
            workspace_id,
            provider
        ),

    CONSTRAINT provider_credentials_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT provider_credentials_provider_not_empty
        CHECK (length(trim(provider)) > 0),

    CONSTRAINT provider_credentials_key_version_valid
        CHECK (key_version >= 1)
);

CREATE INDEX IF NOT EXISTS idx_provider_credentials_workspace
    ON provider_credentials(workspace_id);

CREATE INDEX IF NOT EXISTS idx_provider_credentials_enabled
    ON provider_credentials(
        workspace_id,
        enabled
    );

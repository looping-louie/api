PRAGMA foreign_keys = ON;

CREATE TABLE linked_services (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    key_trimmed TEXT,
    key_ciphertext TEXT,
    key_version INTEGER NOT NULL DEFAULT 1,
    base_url TEXT,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (workspace_id, name),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(provider_type)) > 0),
    CHECK (enabled IN (0, 1)),
    CHECK (key_version >= 1),
    CHECK (version >= 1)
);

CREATE INDEX idx_linked_services_workspace
    ON linked_services(workspace_id);

CREATE INDEX idx_linked_services_provider_type
    ON linked_services(workspace_id, provider_type);
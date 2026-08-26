PRAGMA foreign_keys = OFF;
PRAGMA legacy_alter_table = ON;

ALTER TABLE linked_services RENAME TO linked_services_legacy;

CREATE TABLE linked_services (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
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

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE RESTRICT,

    UNIQUE (user_id, name),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(provider_type)) > 0),
    CHECK (enabled IN (0, 1)),
    CHECK (key_version >= 1),
    CHECK (version >= 1)
);

INSERT INTO linked_services (
    id, user_id, name, provider_type, enabled, key_trimmed, key_ciphertext,
    key_version, base_url, version, created_at, updated_at
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
    legacy.name,
    legacy.provider_type,
    legacy.enabled,
    legacy.key_trimmed,
    legacy.key_ciphertext,
    legacy.key_version,
    legacy.base_url,
    legacy.version,
    legacy.created_at,
    legacy.updated_at
FROM linked_services_legacy AS legacy;

DROP TABLE linked_services_legacy;

CREATE INDEX idx_linked_services_user
    ON linked_services(user_id);

CREATE INDEX idx_linked_services_provider_type
    ON linked_services(user_id, provider_type);

PRAGMA legacy_alter_table = OFF;
PRAGMA foreign_keys = ON;

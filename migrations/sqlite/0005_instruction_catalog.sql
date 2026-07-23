PRAGMA foreign_keys = ON;

CREATE TEMP TABLE instructions_legacy_data AS
SELECT
    id,
    workspace_id,
    instruction_type,
    name,
    name_key,
    description,
    content,
    metadata_json,
    version,
    created_at,
    updated_at
FROM instructions;

DROP TABLE instructions;

CREATE TABLE instructions (
    id TEXT PRIMARY KEY,
    instruction_type TEXT NOT NULL,
    origin TEXT NOT NULL,
    owner_workspace_id TEXT,
    source_instruction_id TEXT,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    catalog_version INTEGER,
    checksum TEXT,
    enabled_by_default INTEGER NOT NULL DEFAULT 0,
    deprecated INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (owner_workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    FOREIGN KEY (source_instruction_id)
        REFERENCES instructions(id)
        ON DELETE SET NULL,

    CHECK (instruction_type IN ('persona', 'skill')),
    CHECK (origin IN ('builtin', 'custom', 'marketplace')),
    CHECK (
        (origin = 'custom' AND owner_workspace_id IS NOT NULL)
        OR (
            origin IN ('builtin', 'marketplace')
            AND owner_workspace_id IS NULL
        )
    ),
    CHECK (
        origin = 'custom'
        OR source_instruction_id IS NULL
    ),
    CHECK (
        source_instruction_id IS NULL
        OR source_instruction_id <> id
    ),
    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(name_key)) > 0),
    CHECK (json_valid(metadata_json)),
    CHECK (json_type(metadata_json) = 'object'),
    CHECK (
        (origin = 'custom' AND catalog_version IS NULL)
        OR (
            origin IN ('builtin', 'marketplace')
            AND catalog_version IS NOT NULL
            AND catalog_version >= 1
        )
    ),
    CHECK (
        (origin = 'custom' AND checksum IS NULL)
        OR (
            origin IN ('builtin', 'marketplace')
            AND checksum IS NOT NULL
            AND length(checksum) = 64
            AND checksum = lower(checksum)
            AND checksum NOT GLOB '*[^0-9a-f]*'
        )
    ),
    CHECK (enabled_by_default IN (0, 1)),
    CHECK (deprecated IN (0, 1)),
    CHECK (version >= 1)
);

INSERT INTO instructions (
    id,
    instruction_type,
    origin,
    owner_workspace_id,
    source_instruction_id,
    name,
    name_key,
    description,
    content,
    metadata_json,
    catalog_version,
    checksum,
    enabled_by_default,
    deprecated,
    version,
    created_at,
    updated_at
)
SELECT
    id,
    instruction_type,
    'custom',
    workspace_id,
    NULL,
    name,
    name_key,
    description,
    content,
    metadata_json,
    NULL,
    NULL,
    1,
    0,
    version,
    created_at,
    updated_at
FROM instructions_legacy_data;

DROP TABLE instructions_legacy_data;

CREATE UNIQUE INDEX idx_instructions_builtin_name
    ON instructions(
        instruction_type,
        name_key
    )
    WHERE origin = 'builtin';

CREATE UNIQUE INDEX idx_instructions_custom_name
    ON instructions(
        owner_workspace_id,
        instruction_type,
        name_key
    )
    WHERE origin = 'custom';

CREATE INDEX idx_instructions_owner_type
    ON instructions(
        owner_workspace_id,
        instruction_type
    );

CREATE INDEX idx_instructions_origin_type
    ON instructions(
        origin,
        instruction_type
    );

CREATE INDEX idx_instructions_owner_updated
    ON instructions(
        owner_workspace_id,
        instruction_type,
        updated_at
    );

CREATE TABLE workspace_instruction_settings (
    workspace_id TEXT NOT NULL,
    instruction_id TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    PRIMARY KEY (
        workspace_id,
        instruction_id
    ),

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    FOREIGN KEY (instruction_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CHECK (enabled IN (0, 1))
);

CREATE INDEX idx_workspace_instruction_settings_enabled
    ON workspace_instruction_settings(
        workspace_id,
        enabled
    );

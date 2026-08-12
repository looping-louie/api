CREATE TEMP TABLE instructions_legacy_data
AS
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
    metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    catalog_version INTEGER,
    checksum TEXT,
    enabled_by_default BOOLEAN NOT NULL DEFAULT FALSE,
    deprecated BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT instructions_owner_workspace_fk
        FOREIGN KEY (owner_workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT instructions_source_fk
        FOREIGN KEY (source_instruction_id)
        REFERENCES instructions(id)
        ON DELETE SET NULL,

    CONSTRAINT instructions_type_valid
        CHECK (instruction_type IN ('persona', 'skill')),

    CONSTRAINT instructions_origin_valid
        CHECK (origin IN ('builtin', 'custom', 'marketplace')),

    CONSTRAINT instructions_owner_valid
        CHECK (
            (origin = 'custom' AND owner_workspace_id IS NOT NULL)
            OR (
                origin IN ('builtin', 'marketplace')
                AND owner_workspace_id IS NULL
            )
        ),

    CONSTRAINT instructions_source_valid
        CHECK (
            (origin = 'custom' OR source_instruction_id IS NULL)
            AND (
                source_instruction_id IS NULL
                OR source_instruction_id <> id
            )
        ),

    CONSTRAINT instructions_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT instructions_name_not_empty
        CHECK (length(trim(name)) > 0),

    CONSTRAINT instructions_name_key_not_empty
        CHECK (length(trim(name_key)) > 0),

    CONSTRAINT instructions_metadata_object
        CHECK (jsonb_typeof(metadata_json) = 'object'),

    CONSTRAINT instructions_catalog_version_valid
        CHECK (
            (origin = 'custom' AND catalog_version IS NULL)
            OR (
                origin IN ('builtin', 'marketplace')
                AND catalog_version IS NOT NULL
                AND catalog_version >= 1
            )
        ),

    CONSTRAINT instructions_checksum_valid
        CHECK (
            (origin = 'custom' AND checksum IS NULL)
            OR (
                origin IN ('builtin', 'marketplace')
                AND checksum IS NOT NULL
                AND checksum ~ '^[0-9a-f]{64}$'
            )
        ),

    CONSTRAINT instructions_version_valid
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
    TRUE,
    FALSE,
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
    enabled BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (
        workspace_id,
        instruction_id
    ),

    CONSTRAINT workspace_instruction_settings_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT workspace_instruction_settings_instruction_fk
        FOREIGN KEY (instruction_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_workspace_instruction_settings_enabled
    ON workspace_instruction_settings(
        workspace_id,
        enabled
    );

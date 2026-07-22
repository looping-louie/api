CREATE TABLE IF NOT EXISTS instructions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    instruction_type TEXT NOT NULL,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT instructions_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT instructions_unique_name
        UNIQUE (
            workspace_id,
            instruction_type,
            name_key
        ),

    CONSTRAINT instructions_type_valid
        CHECK (instruction_type IN ('persona', 'skill')),

    CONSTRAINT instructions_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT instructions_name_not_empty
        CHECK (length(trim(name)) > 0),

    CONSTRAINT instructions_name_key_not_empty
        CHECK (length(trim(name_key)) > 0),

    CONSTRAINT instructions_version_valid
        CHECK (version >= 1),

    CONSTRAINT instructions_metadata_object
        CHECK (jsonb_typeof(metadata_json) = 'object')
);

CREATE INDEX IF NOT EXISTS idx_instructions_workspace_type
    ON instructions(
        workspace_id,
        instruction_type
    );

CREATE INDEX IF NOT EXISTS idx_instructions_workspace_updated
    ON instructions(
        workspace_id,
        instruction_type,
        updated_at
    );

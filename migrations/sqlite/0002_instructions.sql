PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS instructions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    instruction_type TEXT NOT NULL,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (
        workspace_id,
        instruction_type,
        name_key
    ),

    CHECK (instruction_type IN ('persona', 'skill')),
    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(name_key)) > 0),
    CHECK (version >= 1),
    CHECK (json_valid(metadata_json))
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

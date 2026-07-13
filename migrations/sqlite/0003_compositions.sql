PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS compositions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    composition_type TEXT NOT NULL,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    attributes_json TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (
        workspace_id,
        composition_type,
        name_key
    ),

    UNIQUE (
        workspace_id,
        id
    ),

    CHECK (composition_type IN ('council', 'loop')),
    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(name_key)) > 0),
    CHECK (version >= 1),
    CHECK (json_valid(attributes_json))
);

CREATE TABLE IF NOT EXISTS composition_items (
    workspace_id TEXT NOT NULL,
    composition_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    item_json TEXT NOT NULL,

    PRIMARY KEY (
        workspace_id,
        composition_id,
        position
    ),

    FOREIGN KEY (
        workspace_id,
        composition_id
    )
        REFERENCES compositions(
            workspace_id,
            id
        )
        ON DELETE CASCADE,

    CHECK (position >= 0),
    CHECK (json_valid(item_json))
);

CREATE TABLE IF NOT EXISTS resource_dependencies (
    workspace_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,

    PRIMARY KEY (
        workspace_id,
        source_type,
        source_id,
        target_type,
        target_id,
        relation,
        position
    ),

    FOREIGN KEY (
        workspace_id,
        source_id
    )
        REFERENCES compositions(
            workspace_id,
            id
        )
        ON DELETE CASCADE,

    CHECK (length(trim(source_type)) > 0),
    CHECK (length(trim(source_id)) > 0),
    CHECK (length(trim(target_type)) > 0),
    CHECK (length(trim(target_id)) > 0),
    CHECK (length(trim(relation)) > 0),
    CHECK (position >= 0)
);

CREATE INDEX IF NOT EXISTS idx_compositions_workspace_type
    ON compositions(
        workspace_id,
        composition_type
    );

CREATE INDEX IF NOT EXISTS idx_compositions_workspace_updated
    ON compositions(
        workspace_id,
        composition_type,
        updated_at
    );

CREATE INDEX IF NOT EXISTS idx_composition_items_composition
    ON composition_items(
        workspace_id,
        composition_id,
        position
    );

CREATE INDEX IF NOT EXISTS idx_resource_dependencies_target
    ON resource_dependencies(
        workspace_id,
        target_type,
        target_id
    );

CREATE INDEX IF NOT EXISTS idx_resource_dependencies_source
    ON resource_dependencies(
        workspace_id,
        source_type,
        source_id
    );

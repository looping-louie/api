CREATE TABLE IF NOT EXISTS compositions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    composition_type TEXT NOT NULL,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    attributes_json JSONB NOT NULL DEFAULT '{}'::JSONB,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT compositions_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT compositions_unique_name
        UNIQUE (
            workspace_id,
            composition_type,
            name_key
        ),

    CONSTRAINT compositions_workspace_id_unique
        UNIQUE (
            workspace_id,
            id
        ),

    CONSTRAINT compositions_type_valid
        CHECK (composition_type IN ('council', 'loop')),

    CONSTRAINT compositions_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT compositions_name_not_empty
        CHECK (length(trim(name)) > 0),

    CONSTRAINT compositions_name_key_not_empty
        CHECK (length(trim(name_key)) > 0),

    CONSTRAINT compositions_version_valid
        CHECK (version >= 1),

    CONSTRAINT compositions_attributes_object
        CHECK (jsonb_typeof(attributes_json) = 'object')
);

CREATE TABLE IF NOT EXISTS composition_items (
    workspace_id TEXT NOT NULL,
    composition_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    item_json JSONB NOT NULL,

    PRIMARY KEY (
        workspace_id,
        composition_id,
        position
    ),

    CONSTRAINT composition_items_composition_fk
        FOREIGN KEY (
            workspace_id,
            composition_id
        )
        REFERENCES compositions(
            workspace_id,
            id
        )
        ON DELETE CASCADE,

    CONSTRAINT composition_items_position_valid
        CHECK (position >= 0),

    CONSTRAINT composition_items_json_object
        CHECK (jsonb_typeof(item_json) = 'object')
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

    CONSTRAINT resource_dependencies_source_fk
        FOREIGN KEY (
            workspace_id,
            source_id
        )
        REFERENCES compositions(
            workspace_id,
            id
        )
        ON DELETE CASCADE,

    CONSTRAINT resource_dependencies_source_type_not_empty
        CHECK (length(trim(source_type)) > 0),

    CONSTRAINT resource_dependencies_source_id_not_empty
        CHECK (length(trim(source_id)) > 0),

    CONSTRAINT resource_dependencies_target_type_not_empty
        CHECK (length(trim(target_type)) > 0),

    CONSTRAINT resource_dependencies_target_id_not_empty
        CHECK (length(trim(target_id)) > 0),

    CONSTRAINT resource_dependencies_relation_not_empty
        CHECK (length(trim(relation)) > 0),

    CONSTRAINT resource_dependencies_position_valid
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

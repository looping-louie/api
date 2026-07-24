DROP TABLE IF EXISTS resource_dependencies;
DROP TABLE IF EXISTS composition_items;
DROP TABLE IF EXISTS compositions;

CREATE TABLE loops (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    flow TEXT NOT NULL,
    status TEXT NOT NULL,
    stop_conditions_json JSONB NOT NULL,
    output_contract_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT NOT NULL,

    CONSTRAINT loops_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT loops_workspace_id_unique
        UNIQUE (workspace_id, id),

    CONSTRAINT loops_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT loops_title_not_empty
        CHECK (length(trim(title)) > 0),

    CONSTRAINT loops_flow_valid
        CHECK (flow IN ('direct', 'refinement', 'roundtable')),

    CONSTRAINT loops_status_valid
        CHECK (status IN ('active', 'disabled', 'archived')),

    CONSTRAINT loops_created_by_not_empty
        CHECK (length(trim(created_by)) > 0),

    CONSTRAINT loops_updated_by_not_empty
        CHECK (length(trim(updated_by)) > 0)
);

CREATE TABLE loop_agents (
    workspace_id TEXT NOT NULL,
    loop_id TEXT NOT NULL,
    position INTEGER NOT NULL,
    id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    role TEXT NOT NULL,

    PRIMARY KEY (workspace_id, loop_id, position),
    UNIQUE (workspace_id, loop_id, id),

    CONSTRAINT loop_agents_loop_fk
        FOREIGN KEY (workspace_id, loop_id)
        REFERENCES loops(workspace_id, id)
        ON DELETE CASCADE,

    CONSTRAINT loop_agents_position_valid
        CHECK (position >= 0),

    CONSTRAINT loop_agents_id_not_empty
        CHECK (length(trim(id)) > 0),

    CONSTRAINT loop_agents_model_not_empty
        CHECK (length(trim(model_id)) > 0),

    CONSTRAINT loop_agents_persona_not_empty
        CHECK (length(trim(persona_id)) > 0),

    CONSTRAINT loop_agents_role_valid
        CHECK (role IN ('generator', 'reviewer', 'aggregator'))
);

CREATE TABLE loop_changelog_entries (
    id TEXT PRIMARY KEY,
    loop_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL,
    diff_json JSONB,
    content_json JSONB,

    CONSTRAINT loop_changelog_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT loop_changelog_loop_id_not_empty
        CHECK (length(trim(loop_id)) > 0),

    CONSTRAINT loop_changelog_change_type_valid
        CHECK (
            change_type IN (
                'created',
                'updated',
                'enabled',
                'disabled',
                'archived',
                'deleted'
            )
        ),

    CONSTRAINT loop_changelog_actor_not_empty
        CHECK (length(trim(actor_id)) > 0)
);

CREATE INDEX idx_loops_workspace_updated
    ON loops(workspace_id, updated_at DESC);

CREATE INDEX idx_loop_agents_persona
    ON loop_agents(workspace_id, persona_id);

CREATE INDEX idx_loop_changelog_lookup
    ON loop_changelog_entries(
        workspace_id,
        loop_id,
        changed_at DESC
    );

PRAGMA foreign_keys = ON;

CREATE TABLE loops (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    flow TEXT NOT NULL,
    status TEXT NOT NULL,
    stop_conditions_json TEXT NOT NULL,
    output_contract_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    UNIQUE (workspace_id, id),

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(title)) > 0),
    CHECK (flow IN ('direct', 'refinement', 'roundtable')),
    CHECK (status IN ('active', 'disabled', 'archived')),
    CHECK (json_valid(stop_conditions_json)),
    CHECK (json_valid(output_contract_json)),
    CHECK (length(trim(created_by)) > 0),
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

    FOREIGN KEY (workspace_id, loop_id)
        REFERENCES loops(workspace_id, id)
        ON DELETE CASCADE,

    CHECK (position >= 0),
    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(model_id)) > 0),
    CHECK (length(trim(persona_id)) > 0),
    CHECK (role IN ('generator', 'reviewer', 'aggregator'))
);

CREATE TABLE loop_changelog_entries (
    id TEXT PRIMARY KEY,
    loop_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    change_type TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    diff_json TEXT,
    content_json TEXT,

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(loop_id)) > 0),
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
    CHECK (length(trim(actor_id)) > 0),
    CHECK (diff_json IS NULL OR json_valid(diff_json)),
    CHECK (content_json IS NULL OR json_valid(content_json))
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

PRAGMA foreign_keys = OFF;

DROP TABLE persona_linked_service_selections;
DROP TABLE persona_models;
DROP TABLE provider_credentials;

CREATE TABLE persona_linked_service_selections (
    workspace_id TEXT NOT NULL,
    persona_id TEXT NOT NULL,
    linked_service_id TEXT NOT NULL,
    model_id TEXT NOT NULL,

    PRIMARY KEY (workspace_id, persona_id),

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,
    FOREIGN KEY (persona_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,
    FOREIGN KEY (linked_service_id)
        REFERENCES linked_services(id)
        ON DELETE RESTRICT,

    CHECK (length(trim(workspace_id)) > 0),
    CHECK (length(trim(persona_id)) > 0),
    CHECK (length(trim(linked_service_id)) > 0),
    CHECK (length(trim(model_id)) > 0)
);

CREATE INDEX idx_persona_linked_service_selections_linked_service
    ON persona_linked_service_selections(linked_service_id);

CREATE INDEX idx_persona_linked_service_selections_model
    ON persona_linked_service_selections(model_id);

PRAGMA foreign_keys = ON;

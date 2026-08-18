PRAGMA foreign_keys = ON;

CREATE TABLE persona_linked_service_selections (
    persona_id TEXT PRIMARY KEY,
    linked_service_id TEXT NOT NULL,
    model_id TEXT NOT NULL,

    FOREIGN KEY (persona_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,
    FOREIGN KEY (linked_service_id)
        REFERENCES linked_services(id)
        ON DELETE RESTRICT,

    CHECK (length(trim(persona_id)) > 0),
    CHECK (length(trim(linked_service_id)) > 0),
    CHECK (length(trim(model_id)) > 0)
);

CREATE INDEX idx_persona_linked_service_selections_linked_service
    ON persona_linked_service_selections(linked_service_id);

CREATE INDEX idx_persona_linked_service_selections_model
    ON persona_linked_service_selections(model_id);
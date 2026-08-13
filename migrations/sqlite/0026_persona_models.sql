CREATE TABLE persona_models (
    persona_id TEXT PRIMARY KEY,
    model_id TEXT NOT NULL,

    FOREIGN KEY (persona_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CHECK (length(trim(model_id)) > 0)
);

CREATE INDEX idx_persona_models_model
    ON persona_models(model_id);

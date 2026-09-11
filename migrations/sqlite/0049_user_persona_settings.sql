CREATE TABLE user_persona_settings (
    user_id TEXT NOT NULL,
    instruction_id TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    PRIMARY KEY (user_id, instruction_id),

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    FOREIGN KEY (instruction_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CHECK (enabled IN (0, 1))
);

CREATE INDEX idx_user_persona_settings_instruction
    ON user_persona_settings(instruction_id);

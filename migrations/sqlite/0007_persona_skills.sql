PRAGMA foreign_keys = ON;

CREATE TABLE persona_skills (
    persona_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    position INTEGER NOT NULL,

    PRIMARY KEY (
        persona_id,
        skill_id
    ),

    UNIQUE (
        persona_id,
        position
    ),

    FOREIGN KEY (persona_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    FOREIGN KEY (skill_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CHECK (position >= 0),
    CHECK (persona_id <> skill_id)
);

CREATE INDEX idx_persona_skills_skill
    ON persona_skills(skill_id);

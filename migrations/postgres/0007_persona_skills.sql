CREATE TABLE persona_skills (
    persona_id TEXT NOT NULL,
    skill_id TEXT NOT NULL,
    position INTEGER NOT NULL,

    CONSTRAINT persona_skills_pk
        PRIMARY KEY (
            persona_id,
            skill_id
        ),

    CONSTRAINT persona_skills_position_unique
        UNIQUE (
            persona_id,
            position
        ),

    CONSTRAINT persona_skills_persona_fk
        FOREIGN KEY (persona_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CONSTRAINT persona_skills_skill_fk
        FOREIGN KEY (skill_id)
        REFERENCES instructions(id)
        ON DELETE CASCADE,

    CONSTRAINT persona_skills_position_valid
        CHECK (position >= 0),

    CONSTRAINT persona_skills_distinct_ids
        CHECK (persona_id <> skill_id)
);

CREATE INDEX idx_persona_skills_skill
    ON persona_skills(skill_id);

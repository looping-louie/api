PRAGMA foreign_keys = OFF;

ALTER TABLE loop_run_idempotency
    RENAME TO loop_run_idempotency_legacy;

CREATE TABLE loop_run_idempotency (
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    token_revision INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, run_id, token_revision, idempotency_key),

    FOREIGN KEY (workspace_id, run_id)
        REFERENCES loop_runs(workspace_id, id)
        ON DELETE CASCADE,

    CHECK (token_revision >= 0),
    CHECK (length(trim(idempotency_key)) > 0),
    CHECK (json_valid(response_json))
);

INSERT INTO loop_run_idempotency
SELECT * FROM loop_run_idempotency_legacy;

DROP TABLE loop_run_idempotency_legacy;

PRAGMA foreign_keys = ON;
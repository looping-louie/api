CREATE TABLE users (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,

    CHECK (length(trim(id)) > 0)
);

INSERT INTO users (id, created_at, updated_at)
SELECT
    user_id,
    MIN(created_at),
    MAX(created_at)
FROM workspace_memberships
GROUP BY user_id;
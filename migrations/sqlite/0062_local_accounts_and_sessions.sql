ALTER TABLE users
    ADD COLUMN username TEXT;

ALTER TABLE users
    ADD COLUMN password_hash TEXT;

ALTER TABLE users
    ADD COLUMN role TEXT NOT NULL DEFAULT 'member'
    CHECK (role IN ('admin', 'member'));

ALTER TABLE users
    ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1
    CHECK (is_active IN (0, 1));

CREATE UNIQUE INDEX idx_users_username_unique
    ON users(lower(username))
    WHERE username IS NOT NULL;

CREATE TABLE user_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,

    FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(token_hash)) > 0)
);

CREATE INDEX idx_user_sessions_token_hash
    ON user_sessions(token_hash);

CREATE INDEX idx_user_sessions_expiration
    ON user_sessions(expires_at);

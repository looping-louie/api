CREATE TABLE service_accounts (
    id TEXT PRIMARY KEY,
    administrator_id TEXT NOT NULL,
    name TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used_at TEXT,
    expires_at TEXT,
    revoked_at TEXT,

    FOREIGN KEY (administrator_id)
        REFERENCES users(id)
        ON DELETE RESTRICT,

    CHECK (length(trim(id)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(token_hash)) > 0)
);

CREATE TABLE service_account_projects (
    service_account_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    created_at TEXT NOT NULL,

    PRIMARY KEY (service_account_id, project_id),

    FOREIGN KEY (service_account_id)
        REFERENCES service_accounts(id)
        ON DELETE CASCADE,
    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_service_accounts_token_hash
    ON service_accounts(token_hash);

CREATE INDEX idx_service_accounts_administrator_id
    ON service_accounts(administrator_id);

CREATE INDEX idx_service_account_projects_project_id
    ON service_account_projects(project_id);

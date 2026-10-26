CREATE TABLE worker_instances (
    id TEXT PRIMARY KEY,
    registered_at TEXT NOT NULL,
    last_heartbeat_at TEXT NOT NULL,
    harnesses_json TEXT NOT NULL,

    CHECK (length(trim(id)) > 0),
    CHECK (json_valid(harnesses_json))
);

CREATE TABLE worker_project_enablements (
    worker_instance_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    enabled_at TEXT NOT NULL,

    PRIMARY KEY (worker_instance_id, project_id),
    FOREIGN KEY (worker_instance_id)
        REFERENCES worker_instances(id)
        ON DELETE CASCADE,
    FOREIGN KEY (project_id)
        REFERENCES projects(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_worker_project_enablements_project
    ON worker_project_enablements(project_id);
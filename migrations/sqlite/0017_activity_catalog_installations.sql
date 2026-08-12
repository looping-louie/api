CREATE TABLE activity_catalog_installations (
    workspace_id TEXT NOT NULL,
    catalog_activity_id TEXT NOT NULL,
    activity_id TEXT NOT NULL,
    installed_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, catalog_activity_id),

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(catalog_activity_id)) > 0),
    CHECK (length(trim(activity_id)) > 0)
);
PRAGMA foreign_keys = ON;

CREATE TABLE loop_catalog_installations (
    workspace_id TEXT NOT NULL,
    catalog_loop_id TEXT NOT NULL,
    loop_id TEXT NOT NULL,
    installed_at TEXT NOT NULL,

    PRIMARY KEY (workspace_id, catalog_loop_id),

    FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CHECK (length(trim(catalog_loop_id)) > 0),
    CHECK (length(trim(loop_id)) > 0)
);

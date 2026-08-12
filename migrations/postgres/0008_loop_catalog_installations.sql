CREATE TABLE loop_catalog_installations (
    workspace_id TEXT NOT NULL,
    catalog_loop_id TEXT NOT NULL,
    loop_id TEXT NOT NULL,
    installed_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT loop_catalog_installations_pk
        PRIMARY KEY (workspace_id, catalog_loop_id),

    CONSTRAINT loop_catalog_installations_workspace_fk
        FOREIGN KEY (workspace_id)
        REFERENCES workspaces(id)
        ON DELETE CASCADE,

    CONSTRAINT loop_catalog_installations_catalog_id_not_empty
        CHECK (length(trim(catalog_loop_id)) > 0),

    CONSTRAINT loop_catalog_installations_loop_id_not_empty
        CHECK (length(trim(loop_id)) > 0)
);

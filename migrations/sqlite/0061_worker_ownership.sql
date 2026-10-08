ALTER TABLE worker_instances
    ADD COLUMN owner_user_id TEXT
    REFERENCES users(id);

UPDATE worker_instances
SET owner_user_id = (
    SELECT membership.user_id
    FROM worker_project_enablements AS enablement
    INNER JOIN project_memberships AS membership
        ON membership.project_id = enablement.project_id
    WHERE enablement.worker_instance_id = worker_instances.id
        AND membership.role = 'owner'
    ORDER BY enablement.enabled_at ASC, membership.user_id ASC
    LIMIT 1
);

CREATE INDEX idx_worker_instances_owner
    ON worker_instances(owner_user_id);

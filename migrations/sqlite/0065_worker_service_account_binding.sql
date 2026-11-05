ALTER TABLE worker_instances
    ADD COLUMN service_account_id TEXT
    REFERENCES service_accounts(id)
    ON DELETE SET NULL;

CREATE INDEX idx_worker_instances_service_account_id
    ON worker_instances(service_account_id);

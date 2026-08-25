ALTER TABLE workers
    ADD COLUMN harnesses_json TEXT NOT NULL
    DEFAULT '[{"kind":"louie","version":"v1","config":{}}]'
    CHECK (json_valid(harnesses_json));
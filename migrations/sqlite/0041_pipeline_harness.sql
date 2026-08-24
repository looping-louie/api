ALTER TABLE pipelines
    ADD COLUMN harness_json TEXT NOT NULL
    DEFAULT '{"kind":"louie","version":"v1","config":{}}'
    CHECK (json_valid(harness_json));
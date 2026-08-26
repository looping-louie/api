ALTER TABLE users ADD COLUMN settings_json TEXT NOT NULL DEFAULT '{"default_harness":null}'
CHECK (json_valid(settings_json));
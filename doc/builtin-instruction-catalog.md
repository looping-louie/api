# Builtin instruction catalog

Builtin skills and personas are versioned application resources. Their
manifests and Markdown live under:

```text
src/app/catalogs/
├── skills/
│   ├── registry.json
│   └── content/
└── personas/
    ├── registry.json
    └── content/
```

At startup the application validates these files and synchronizes them into
SQL. API and execution services read instructions only from SQL after that
point.

## Add a builtin

1. Add one manifest entry to the appropriate `registry.json`.
2. Assign a stable, never-reused ID:
   `builtin:skill:<key>` or `builtin:persona:<key>`.
3. Set an explicit `content_path` and create exactly that Markdown file.
4. Keep identity, description, version and structured metadata in the
   manifest. Keep only effective prompt instructions in Markdown.
5. For a persona, use stable builtin skill IDs in `skill_ids`.
6. Run `make catalog-check` and the test suite.

## Update a builtin

Change the manifest or Markdown and increment `version`. Production enables
`LOUIE_CATALOG_STRICT_VERSIONING`, so a changed checksum with an unchanged
catalog version is rejected. Development may accept it with a warning to make
iteration easier.

The next application bootstrap updates SQL in a single transaction. Existing
executions remain reproducible because each run owns an
`instructions-snapshot.json` containing the exact definitions it used.

## Retire a builtin

Remove its manifest entry, but never reuse its ID. Synchronization marks the
SQL row as deprecated; it does not delete it. New loops cannot select a
deprecated instruction, while historical references can still resolve it.

## A brief note on catalog synchronization

Also called

- Seeded reference data
- Catalog synchronization
- Bootstrap or migration-managed data
- Materialized runtime catalog

this pattern is common, especially when an application has version-controlled
reference content that must become runtime-queryable, workspace-aware data.

In this case, the design is:

```txt
Git-tracked manifest + Markdown
        -> validate and synchronize at startup
SQL runtime projection
        -> API, availability resolution, loop-run execution
```

The important distinction is that the files are still the authored source of truth for builtins, while SQL is the operational source of truth once the application is running.

This is a good fit here because SQL enables things that repository files do not provide cleanly:

Workspace-specific enablement and availability.
Custom copies of immutable builtins.
Ownership and access control.
Deprecation without losing historical references.
Atomic updates and consistency constraints.
Fast, uniform runtime queries.
Reproducible execution snapshots based on the exact effective library.

# Builtin Persona and Skill Catalog

Builtin Personas and Skills are versioned application resources. Their
manifests and Markdown live under:

```text
src/app/catalogs/
|-- skills/
|   |-- registry.json
|   `-- items/
`-- personas/
    |-- registry.json
    `-- items/
```

At startup the application loads both resource sets into one
`PersonaSkillCatalog`, validates their IDs and cross-references, and
synchronizes the result into SQL. API and execution services read instruction
records only from SQL after that point.

## Add a builtin

1. Add one manifest entry to the appropriate `registry.json`.
2. Assign a stable, never-reused ID:
   `builtin:skill:<key>` or `builtin:persona:<key>`.
3. Set an explicit `content_path` and create exactly that Markdown file.
4. Keep identity, description, version, and structured metadata in the
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
SQL row as deprecated; it does not delete it. New Activity configurations cannot
select a deprecated instruction, while historical references can still resolve
it.

## Catalog synchronization

This pattern is also called seeded reference data, catalog synchronization,
bootstrap or migration-managed data, or a materialized runtime catalog. It is
useful when version-controlled reference content must become runtime-queryable
and workspace-aware data.

The design is:

```text
Git-tracked Persona and Skill manifests + Markdown
    -> load PersonaSkillCatalog and synchronize at startup
SQL runtime projection
        -> API, availability resolution, loop-run execution
```

The files remain the authored source of truth for builtins. SQL is the
operational source of truth once the application is running.

SQL provides:

- workspace-specific enablement and availability;
- custom copies of immutable builtins;
- ownership and access control;
- deprecation without losing historical references;
- atomic updates and consistency constraints;
- fast, uniform runtime queries;
- reproducible execution snapshots based on the exact effective library.

## Runtime boundary

Startup has one ordered catalog boundary:

```text
run migrations
    v
load and validate packaged Persona and Skill catalog
    v
synchronize built-in Personas and Skills into SQL
    v
ensure local tenant
    v
construct repositories and services
```

Only startup reads packaged Markdown. API, loop resolution, and execution read
the effective workspace library from SQL. Builtins are globally shared and
immutable through the API; workspaces can enable, disable, or duplicate them.
Custom instructions belong to one workspace and remain editable.

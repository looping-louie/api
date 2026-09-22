# Looping Louie

Looping Louie API is the FastAPI control plane for Looping Louie. It manages
Users, Projects, configuration resources, Pipeline and Activity definitions,
runtime Workers, and durable execution state. Runtime workers perform local
checkout actions and report checkpoint outcomes to this service.

## Installation

Clone the repository and run:

```sh
make install
```

This command will:

- Create the Python virtual environment in `env/`.
- Install every dependency from `requirements.txt`.
- Create a `.env.local` file if it does not already exist.
- Generate a Fernet encryption key.
- Store the generated key as `LOUIE_ENCRYPTION_KEY` in `.env.local`.

The installer never overwrites an existing `.env.local`, because changing
`LOUIE_ENCRYPTION_KEY` would make previously encrypted provider credentials
unreadable.

## Configuration

`make install` creates `.env.local` with these defaults:

```text
LOUIE_ENCRYPTION_KEY=<generated Fernet key>
LOUIE_DB_PATH=runtime/db/looping-louie.db
LOUIE_CATALOG_STRICT_VERSIONING=false
```

`LOUIE_ENCRYPTION_KEY` is the Looping Louie master encryption key. It encrypts
provider credentials before they are stored in SQLite. Do not commit it, log it
or regenerate it while encrypted credentials still exist.

`LOUIE_CATALOG_STRICT_VERSIONING` defaults to `false` for development. Set it
to `true` in production so a builtin checksum change requires an incremented
`catalog_version`.

Set `LOUIE_DEV_AUTH=true` to enable local development authentication. Requests
without `X-User-ID` then use `LOUIE_DEV_USER_ID`, which defaults to
`local-user`.

To deliberately replace the local configuration and generate a new encryption
key:

```sh
make reset-config
```

This is destructive for existing encrypted provider credentials. Remove or
reconfigure those credentials after resetting the key.

## Execution

Start the development server:

```sh
make dev
```

Or use the existing alias:

```sh
make run
```

The Makefile always starts Uvicorn with the virtual environment interpreter and
exports the values from `.env.local`.

The local SQLite database at `runtime/db/looping-louie.db` is an
intentional runtime artifact and is ignored by Git. Set `LOUIE_DB_PATH` in
`.env.local` to store it outside the repository when preferred.

The API will be available (by default) at:

```text
http://127.0.0.1:2000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:2000/docs
```

## Development

See [Docker](doc/docker.md) to run the production API image with Docker Compose.

### SQLite Migrations

SQLite migration files are immutable once committed. Do not edit an existing
migration for any reason, including whitespace or terminal-newline changes.
Create a new forward migration instead.

Migration checksums cover the exact file bytes. A terminal newline inserted by
an editor after a migration has been applied changes its checksum and prevents
the application from starting against that database. The `.editorconfig`
exception for `migrations/**/*.sql` prevents automatic save-time whitespace
rewrites; it does not make post-application edits safe.

Every new SQLite migration must be added to the checksum manifest in
`tests/integration/migrations/test_sqlite_migration_checksums.py`. That test
protects the exact bytes of committed migrations and must pass before the
migration is committed.

## Docker

# Looping Louie

Looping Louie API is the decision engine for iterative LLM software development.

Instead of relying on a single model, Looping Louie orchestrates a development
loop where:

1. A generator proposes code changes.
2. One or more specialised reviewer skills validate those changes.
3. The generator iterates until every reviewer approves or the maximum number
   of iterations is reached.

The runtime is provider-independent and designed to be reproducible, observable
and deployable in SaaS and on-premise environments.

---

## Big picture

Lets take a step back and remember: Looping Louie is an app for fast
AI-driven development, which intends to automate the dev cycle.

Ideally, an user will create a repo (looping-louie-test) and, by means of
interacting with the lopping-louie CLI (which internally calls to the API),
will be able to rapidly implement whatever project is in their mind.

## Features

- Iterative generator and reviewer workflow
- Multiple independent review skills
- Checkpoint-based API-CLI orchestration
- Automatic Git diff generation
- JSON-based file operations
- API-guided local execution in CLI
- One commit per approved task (executed by CLI)
- Complete execution traces
- Token and latency metrics
- Provider-independent architecture
- Encrypted provider credential storage
- Local SQLite persistence for development and simple on-premise deployments

---

## Installation

Clone the repository and run:

```sh
make install
```

This command will:

- Create the Python virtual environment in `env/`.
- Install every dependency from `requirements.txt`.
- Create `.env.local` when it does not already exist.
- Generate a Fernet encryption key.
- Store the generated key as `LOUIE_ENCRYPTION_KEY` in `.env.local`.

The installer never overwrites an existing `.env.local`, because changing
`LOUIE_ENCRYPTION_KEY` would make previously encrypted provider credentials
unreadable.

Ensure `requirements.txt` contains the provider feature dependencies:

```text
aiosqlite
cryptography
httpx
python-dotenv
```

---

## Configuration

After installation, populate the provider API keys required by the execution
runtime in `.env.local`:

```text
TOGETHER_API_KEY=
OPENAI_API_KEY=
```

The installer also creates these local provider settings:

```text
LOUIE_ENCRYPTION_KEY=<generated Fernet key>
LOUIE_DB_PATH=.looping-louie/data/looping-louie.db
LOUIE_CATALOG_STRICT_VERSIONING=false
```

`LOUIE_ENCRYPTION_KEY` is the Looping Louie master encryption key. It encrypts
provider credentials before they are stored in SQLite. Do not commit it, log it
or regenerate it while encrypted credentials still exist.

`LOUIE_CATALOG_STRICT_VERSIONING` defaults to `false` for development. Set it
to `true` in production so a builtin checksum change requires an incremented
`catalog_version`.

Add these patterns to `.gitignore`:

```gitignore
.env
.env.local
*.db
*.db-shm
*.db-wal
.looping-louie/
```

To deliberately replace the local configuration and generate a new encryption
key:

```sh
make reset-config
```

This is destructive for existing encrypted provider credentials. Remove or
reconfigure those credentials after resetting the key.

---

## Running the API

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

The API is available at:

```text
http://127.0.0.1:8000
```

Interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

## Usage

Looping Louie currently exposes these endpoints.

| Endpoint | Purpose |
|----------|---------|
| `/task/start` | Start one checkpoint-based task execution. |
| `/task/continue` | Advance one checkpoint transition. |
| `/task/{run_id}` | Read latest checkpoint state for a task run. |
| `/meeting/run` | Run a structured multi-persona meeting. |

See the complete API documentation:

- [`doc/API.md`](doc/API.md)

---

## Repository Requirements

Before running Looping Louie against a target repository:

- The target directory must be a Git repository.
- The repository must have no uncommitted changes.

Looping Louie refuses to execute against a dirty repository to keep runs
deterministic.

---

## Documentation

Project documentation is organised under `doc/`.

| Document | Purpose |
|---|---|
| `architecture.md` | Runtime architecture and execution lifecycle. |
| `philosophy.md` | Design principles and engineering philosophy. |
| `roadmap.md` | Planned architectural evolution. |
| `API.md` | HTTP API reference. |
| `development-log.md` | Engineering logbook and execution notes. |

---

## High-Level Execution Flow

```
task request
      │
      ▼
/task/start
      │
      ▼
CLI builds snapshot and runs local action
      │
      ▼
/task/continue
      │
      ▼
Planner and reviewer services
      │
      ▼
Generator model
      │
      ▼
JSON file operations
      │
      ▼
Apply operations
      │
      ▼
Git diff
      │
      ▼
Reviewer skills
      │
      ▼
Approved?
 │           │
 │ No        │ Yes
 ▼           ▼
Retry    Commit allowed
          (CLI commits)
```

---

## Current Status

Looping Louie is currently an MVP focused on validating the execution runtime.

The current implementation supports:

- checkpoint task execution contracts;
- multi-skill review;
- automatic commits;
- execution traces;
- run persistence;
- reusable review skills.

Future work is tracked in `docs/roadmap.md`.

---

## License

_Not yet defined._

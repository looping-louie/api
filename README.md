# Looping Louie

Looping Louie is a Harness-as-a-Service runtime for iterative LLM software development.

Instead of relying on a single model, Looping Louie orchestrates a development loop where:

1. a generator proposes code changes;
2. one or more specialised reviewer skills validate those changes;
3. the generator iterates until every reviewer approves or a maximum number of iterations is reached.

The runtime is provider-independent and designed to be reproducible, observable and enterprise deployable.

---

# Features

- Iterative generator/reviewer workflow
- Multiple independent review skills
- Git worktree isolation
- Automatic Git diff generation
- JSON-based file operations
- Automatic task execution from `tasks.json`
- One commit per approved task
- Complete execution traces
- Token and latency metrics
- Provider-independent architecture

---

# Installation

Clone the repository and install the project:

```sh
make install
```

This command will:

- create the Python virtual environment;
- install all dependencies;
- create a `.env` file if it does not already exist.

---

# Configuration

Populate the generated `.env` file:

```text
TOGETHER_API_KEY=
OPENAI_API_KEY=
```

---

# Running the API

Start the development server:

```sh
make run
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

# Usage

Looping Louie currently exposes two endpoints.

| Endpoint | Purpose |
|----------|---------|
| `/run-harness` | Execute a single harness run. |
| `/run-tasks` | Execute an entire `tasks.json` backlog. |

See the complete API documentation:

- [`docs/API.md`](doc/API.md)

---

# Repository Requirements

Before running Looping Louie:

- the target directory must be a Git repository;
- the repository must have no uncommitted changes.

Looping Louie refuses to execute against a dirty repository to guarantee deterministic results.

---

# Documentation

Project documentation is organised under `docs/`.

| Document | Purpose |
|----------|---------|
| `architecture.md` | Runtime architecture and execution lifecycle. |
| `philosophy.md` | Design principles and engineering philosophy. |
| `roadmap.md` | Planned architectural evolution. |
| `API.md` | HTTP API reference. |
| `development-log.md` | Engineering logbook and execution notes. |

---

# High-Level Execution Flow

```
tasks.json
      │
      ▼
/run-tasks
      │
      ▼
run_harness()
      │
      ▼
Create Git worktree
      │
      ▼
Build repository snapshot
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
Retry    Apply diff
          Commit
```

---

# Current Status

Looping Louie is currently an MVP focused on validating the execution runtime.

The current implementation already supports:

- isolated Git worktrees;
- multi-skill review;
- task backlogs (`tasks.json`);
- automatic commits;
- execution traces;
- run persistence;
- reusable review skills.

Future work is tracked in `doc/roadmap.md`.

---

# License

_Not yet defined._

# Looping Louie

Looping Louie API is the decision engine for iterative LLM software development.

Instead of relying on a single model, Looping Louie orchestrates a development loop where:

1. a generator proposes code changes;
2. one or more specialised reviewer skills validate those changes;
3. the generator iterates until every reviewer approves or a maximum number of iterations is reached.

The runtime is provider-independent and designed to be reproducible, observable and enterprise deployable.

---

## Big picture

Lets take a step back and remember: Looping Louie is an app for fast
AI-driven development, which intends to automate the dev cycle.

Ideally, an user will create a repo (looping-louie-test) and, by means of
interacting with the lopping-louie CLI (which internally calls to the API),
will be able to rapidly implement whatever project is in their mind.

## Features

- Iterative generator/reviewer workflow
- Multiple independent review skills
- Checkpoint-based API-CLI orchestration
- Automatic Git diff generation
- JSON-based file operations
- API-guided local execution in CLI
- One commit per approved task (executed by CLI)
- Complete execution traces
- Token and latency metrics
- Provider-independent architecture

---

## Installation

Clone the repository and install the project:

```sh
make install
```

This command will:

- create the Python virtual environment;
- install all dependencies;
- create a `.env` file if it does not already exist.

---

## Configuration

Populate the generated `.env` file:

```text
TOGETHER_API_KEY=
OPENAI_API_KEY=
```

---

## Running the API

Start the development server:

```sh
make run
```

The API will be available at:

```text
http://127.0.0.1:8000
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

Before running Looping Louie:

- the target directory must be a Git repository;
- the repository must have no uncommitted changes.

Looping Louie refuses to execute against a dirty repository to guarantee deterministic results.

---

## Documentation

Project documentation is organised under `doc/`.

| Document | Purpose |
|----------|---------|
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

The current implementation already supports:

- checkpoint task execution contracts;
- multi-skill review;
- automatic commits;
- execution traces;
- run persistence;
- reusable review skills.

Future work is tracked in `doc/roadmap.md`.

---

## License

_Not yet defined._

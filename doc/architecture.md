# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development. It orchestrates generators, reviewers, and aggregators while the
CLI executes repository changes locally.

The runtime is independent from any programming language, framework, or LLM
provider.

## Components

- [Execution](components/execution.md) describes persisted runs, checkpoints,
  prompts, review, finalisation, artefacts, and metrics.
- [Loops and roles](components/loops-and-roles.md) defines loop flows, agent
  roles, and the loop-run behavior implemented today.
- [Instruction catalog](components/instruction-catalog.md) describes builtin
  instruction ownership, synchronization, and maintenance.
- [Providers](components/providers.md) records provider and model-catalog
  boundaries.
- [Philosophy](components/philosophy.md) contains the project principles and
  long-term direction.

## Repository structure

Top-level packages and modules:

```text
app/

main.py
    HTTP API

routers/
    Endpoint composition

controllers/
    HTTP-level request orchestration

services/
    Application and domain services

catalogs/
    Curated providers, models, loops, and builtin instructions

schemas/
    API contracts and shared models

models/
    Internal domain entities

utils/
    Shared IO and helper utilities
```

## High-level architecture

```text
              Loop definition
                     |
                     v
          Persisted loop run
                     |
                     v
       Generator and reviewers
                     |
                     v
    Operation Contract (JSON operations)
                     |
                     v
           CLI Executes Locally
                     |
                     v
             Reviewer agents
          |
          v
      Aggregator
          |
      Approved?
      |        |
      |No      |Yes
      v        v
 Retry      Commit allowed
             (CLI commits)
             Next workflow item
```

## Ownership boundaries

Workspace lifecycle is CLI-owned. The API persists loop-run orchestration
state and decides whether the next checkpoint is allowed. Multi-step workflow
orchestration is also CLI-owned:

```text
selected loop and input

v

create persisted loop run

v

iterate its `/continue` checkpoint

v

approved?

v

commit

v

record workflow progress

v

next task
```

Execution stops immediately after the first rejected task.

## Current limitations

The current MVP intentionally keeps the architecture simple:

- repository snapshots are static rather than task-aware;
- providers are not yet abstracted behind a common interface;
- reviewers operate on text only, without screenshots;
- file operations replace whole files rather than editing line ranges;
- execution is sequential;
- prompt caching is not yet implemented.

These limitations are tracked separately in `roadmap.md`.

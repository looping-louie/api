# Looping Louie Architecture

Looping Louie API is the decision engine for iterative LLM software
development.

Rather than trusting a single model to generate production-ready code, Looping
Louie orchestrates a structured workflow in which a generator proposes changes,
multiple specialised reviewers evaluate those changes, and the process repeats
until a configurable quality bar is reached.

The runtime is intentionally independent from any specific programming
language, framework or LLM provider.

---

## Repository Structure

Top-level packages and modules:

```text
app/

main.py
    HTTP API

routers/
    Endpoint composition

controllers/
    HTTP-level request orchestration

services/task_checkpoint/
    Loop operation contract parsing

catalogs/
    Curated providers, models, loops and builtin instructions

catalogs/personas/
    Versioned persona manifest and Markdown content

catalogs/skills/
    Versioned skill manifest and Markdown content

schemas/
    API contracts and shared models

models/
    Internal domain entities

utils/
    Shared IO and helper utilities
```

---

## High-Level Architecture

```text
              Loop definition
                     │
                     ▼
          Persisted loop run
                     │
                     ▼
       Generator and reviewers
                     │
                     ▼
    Operation Contract (JSON operations)
                     │
                     ▼
           CLI Executes Locally
                     │
                     ▼
             Reviewer agents
          │
          ▼
      Aggregator
          │
      Approved?
      │        │
      │No      │Yes
      ▼        ▼
 Retry      Commit allowed
             (CLI commits)
             Next workflow item
```

---

## Execution Lifecycle

A persisted loop run follows these steps.

### 1. Create and persist a loop run

The API persists the loop snapshot, run status, checkpoint action, iteration,
and continuation revision in SQLite.

The run also persists a versioned `instructions-snapshot.json`. It contains
the instruction definitions available when the run starts. The same in-memory
snapshot is used for the entire run; execution services do not resolve those
definitions again.

---

### 2. Receive repository context from CLI

CLI sends the repository snapshot context in `collect_snapshot`.

API uses that context to build iteration prompts.

---

### 3. Build prompts

The loop-run generation service creates:

- initial generator prompt
- retry generator prompts
- reviewer prompts

Prompt construction is centralised so orchestration code never builds prompts directly.

---

### 4. Generator execution

The configured generator model receives:

- repository snapshot
- user task
- previous reviewer feedback (on retries)

The generator returns structured JSON describing filesystem operations.

Example:

```json
{
  "operations": [
    {
      "operation": "replace",
      "path": "pages/index.vue",
      "content": "..."
    }
  ]
}
```

---

### 5. Validate operation contract and ask CLI to apply

API validates generator operations contract and returns them in checkpoint
payload.

CLI applies operations locally and reports success/failure in
`apply_operations`.

---

### 6. Receive diff and changed file contents from CLI

CLI sends `final_diff` and changed file contents in `submit_review_input`.

API uses this reviewer input as the decision source of truth.

---

### 7. Reviewer execution

Each configured reviewer agent produces one independent review.

Reviewers receive:

- original task
- git diff
- changed file contents
- persona and skill instructions

Reviewers never receive the entire repository snapshot.

---

### 8. Aggregate review results

Every reviewer agent returns:

- approved
- feedback
- metrics

The aggregator approves the iteration only if every reviewer approves.

Otherwise the feedback is merged and returned to the generator.

---

### 9. Retry

If approval fails:

- repository context is rebuilt
- reviewer feedback is appended
- generator runs again

The loop continues until:

- every reviewer approves
- maximum iterations are reached

---

### 10. Finalisation

If the run succeeds:

- API marks commit handoff as allowed.
- CLI performs the commit and reports the result.

---

## Prompt Lifecycle

Three prompt types currently exist.

### Generator

Contains:

- repository snapshot
- user task

Retry prompts additionally include reviewer feedback.

---

### Reviewer

Contains:

- original task
- git diff
- changed file contents
- review skill

---

### Instruction catalog

Packaged skills and personas are Markdown content documents referenced
explicitly by catalog manifests. Identity, versioning and metadata live in
`registry.json`; Markdown files contain instructions only.

Example:

```text
catalogs/skills/
    registry.json
    content/
        code_review/
            security.md
        planning/
            acceptance_criteria.md
```

Startup has one ordered catalog boundary:

```text
run migrations
    ↓
load and validate packaged catalog
    ↓
synchronize builtins into SQL
    ↓
ensure local tenant
    ↓
construct repositories and services
```

Only startup reads packaged Markdown. API, loop resolution and execution all
read the effective workspace library from SQL. Builtins are globally shared
and immutable through the API; workspaces can enable, disable or duplicate
them. Custom instructions belong to one workspace and remain editable.

See [Builtin instruction catalog](builtin-instruction-catalog.md) for the
maintenance procedure.

---

## Workspace Lifecycle

Workspace lifecycle is CLI-owned.

API persists loop-run orchestration state in SQLite.

---

## Workflow Lifecycle

Multi-step workflow orchestration is CLI-owned.

CLI workflow (conceptual):

```text
selected loop and input

↓

create persisted loop run

↓

iterate its `/continue` checkpoint

↓

approved?

↓

commit

↓

record workflow progress

↓

next task
```

Execution stops immediately after the first rejected task.

---

## Skills

A skill is a reusable review policy.

Examples include:

- code quality
- Nuxt conventions
- UI preservation
- accessibility
- SEO
- security

Projects compose skills.

Skills remain project independent.

---

## Providers

Current providers:

- Anthropic
- NVIDIA
- Ollama
- OpenAI
- Together

The curated model catalog currently contains deployments for Anthropic, OpenAI
and Together. NVIDIA and Ollama are valid configurable providers, but they do
not yet expose selectable curated deployments. Their provider API response
returns a zero model count and an explicit catalog note until model discovery
or supported deployments are added.

The architecture is intentionally provider independent.

Future providers may include:

- Gemini
- enterprise models

The runner should not contain provider-specific logic.

---

## Run Artefacts

Every execution persists enough information for complete inspection.

Typical artefacts include:

- request
- effective instruction snapshot
- response
- prompts
- model responses
- git diffs
- execution trace
- metrics

This makes every run reproducible and debuggable.

---

## Metrics

Metrics are collected for:

- generator
- every reviewer
- complete execution

Current metrics include:

- input tokens
- output tokens
- cached tokens
- reasoning tokens
- duration
- throughput

Future versions will additionally expose execution cost and historical trends.

---

## Design Principles

Looping Louie follows a small number of architectural principles.

- Git is the source of truth.
- Worktrees isolate every execution.
- Generators propose; reviewers validate.
- JSON file operations are preferred over LLM-generated patches.
- Git computes the real diff.
- One reviewer equals one responsibility.
- Prompt construction is centralised.
- Runs are fully observable.
- Instruction definitions are snapshotted once per run.
- Tasks are committed independently.
- Small iterations are preferred over large rewrites.
- Simplicity is preferred over abstraction.
- The runtime owns the workflow; models are interchangeable.

---

## Current Limitations

The current MVP intentionally keeps the architecture simple.

Known limitations include:

- repository snapshots are static rather than task-aware;
- providers are not yet abstracted behind a common interface;
- reviewers operate on text only (no screenshots);
- file operations replace whole files rather than editing line ranges;
- execution is sequential;
- prompt caching is not yet implemented.

These limitations are tracked separately in `roadmap.md`.

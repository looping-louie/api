# Looping Louie Architecture

Looping Louie is a Harness-as-a-Service runtime for iterative LLM software development.

Rather than trusting a single model to generate production-ready code, Looping Louie orchestrates a structured workflow in which a generator proposes changes, multiple specialised reviewers evaluate those changes, and the process repeats until a configurable quality bar is reached.

The runtime is intentionally independent from any specific programming language, framework or LLM provider.

---

# High-Level Architecture

```text
                tasks.json
                     │
                     ▼
             Task Runner (/run-tasks)
                     │
                     ▼
              Harness Runner (/run-harness)
                     │
          ┌──────────┴──────────┐
          │                     │
          ▼                     │
   Workspace Manager            │
          │                     │
          ▼                     │
     Git Worktree               │
          │                     │
          ▼                     │
   Repository Snapshot          │
          │                     │
          ▼                     │
      Prompt Builder            │
          │                     │
          ▼                     │
      Generator Model           │
          │                     │
          ▼                     │
     JSON File Operations       │
          │                     │
          ▼                     │
      File Operations           │
          │                     │
          ▼                     │
      Git Diff Builder          │
          │                     │
          ▼                     │
      Reviewer Skills ◄─────────┘
          │
          ▼
      Aggregator
          │
      Approved?
      │        │
      │No      │Yes
      ▼        ▼
 Retry      Apply diff
             Commit
             Next task
```

---

# Execution Lifecycle

A single harness execution follows these steps.

## 1. Create a workspace

A temporary Git worktree is created from the repository HEAD.

The original repository remains untouched.

Every run receives its own directory under:

```text
.looping-louie/runs/<run_id>/
```

---

## 2. Build repository context

The repository is scanned.

Only relevant source files are included.

Large generated artefacts such as lockfiles, build output and dependencies are ignored.

The resulting snapshot becomes part of the generator prompt.

---

## 3. Build prompts

The Prompt Builder creates:

- initial generator prompt
- retry generator prompts
- reviewer prompts

Prompt construction is centralised so orchestration code never builds prompts directly.

---

## 4. Generator execution

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

## 5. Apply file operations

The runtime validates every operation.

Operations are applied only inside the temporary worktree.

The original repository is still untouched.

---

## 6. Produce the Git diff

Git computes the real diff.

The generator never produces patches directly.

Git is considered the single source of truth.

---

## 7. Reviewer execution

Each configured skill becomes one independent reviewer.

Reviewers receive:

- original task
- git diff
- changed file contents
- skill definition

Reviewers never receive the entire repository snapshot.

---

## 8. Aggregate review results

Every reviewer returns:

- approved
- feedback
- metrics

The aggregator approves the iteration only if every reviewer approves.

Otherwise the feedback is merged and returned to the generator.

---

## 9. Retry

If approval fails:

- repository context is rebuilt
- reviewer feedback is appended
- generator runs again

The loop continues until:

- every reviewer approves
- maximum iterations are reached

---

## 10. Finalisation

If the run succeeds:

- the final diff is applied to the original repository

If running through `/run-tasks`:

- repository changes are committed
- task is marked as completed
- next task begins

---

# Repository Structure

Current modules:

```text
app/

main.py
    HTTP API

runner.py
    Harness orchestration

task_runner.py
    Multi-task execution

workspace.py
    Git worktree lifecycle

repository.py
    Repository snapshot builder

prompt_builder.py
    Prompt construction

FileChangeService.py
    JSON file operations

patcher.py
    Git diff generation

git_ops.py
    Git commit helpers

llm_together.py
    Generator provider

llm_openai.py
    Reviewer provider

skill_loader.py
    Skill loading

run_store.py
    Execution persistence

schemas.py
    API models
```

---

# Prompt Lifecycle

Three prompt types currently exist.

## Generator

Contains:

- repository snapshot
- user task

Retry prompts additionally include reviewer feedback.

---

## Reviewer

Contains:

- original task
- git diff
- changed file contents
- review skill

---

## Skills

Skills are Markdown documents with YAML front matter.

Example:

```text
skills/

code_review/
    small_patch_quality.md

release/
    accessibility.md
```

---

# Workspace Lifecycle

Each harness execution owns one workspace.

```text
.looping-louie/

runs/

<run_id>/

worktree/

generator/

reviewers/

diffs/

request.json

response.json

trace.json
```

The worktree isolates every execution from the original repository.

---

# Task Lifecycle

The `/run` endpoint executes one task.

The `/run-tasks` endpoint executes an entire backlog.

Workflow:

```text
tasks.json

↓

first pending task

↓

run harness

↓

approved?

↓

commit

↓

mark done

↓

next task
```

Execution stops immediately after the first rejected task.

---

# Skills

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

# Providers

Current providers:

- Together (generator)
- OpenAI (reviewers)

The architecture is intentionally provider independent.

Future providers may include:

- Anthropic
- Gemini
- local models
- enterprise models

The runner should not contain provider-specific logic.

---

# Run Artefacts

Every execution persists enough information for complete inspection.

Typical artefacts include:

- request
- response
- prompts
- model responses
- git diffs
- execution trace
- metrics

This makes every run reproducible and debuggable.

---

# Metrics

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

# Design Principles

Looping Louie follows a small number of architectural principles.

- Git is the source of truth.
- Worktrees isolate every execution.
- Generators propose; reviewers validate.
- JSON file operations are preferred over LLM-generated patches.
- Git computes the real diff.
- One reviewer equals one responsibility.
- Prompt construction is centralised.
- Runs are fully observable.
- Tasks are committed independently.
- Small iterations are preferred over large rewrites.
- Simplicity is preferred over abstraction.
- The runtime owns the workflow; models are interchangeable.

---

# Current Limitations

The current MVP intentionally keeps the architecture simple.

Known limitations include:

- repository snapshots are static rather than task-aware;
- providers are not yet abstracted behind a common interface;
- reviewers operate on text only (no screenshots);
- file operations replace whole files rather than editing line ranges;
- execution is sequential;
- prompt caching is not yet implemented.

These limitations are tracked separately in `roadmap.md`.

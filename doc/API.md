# API

Looping Louie currently exposes two HTTP endpoints.

- `/run-harness` executes a single harness run.
- `/run-tasks` executes an entire `tasks.json` backlog.

---

## POST /run-harness

Executes a single task against a repository.

The repository is modified **only if every reviewer approves** before
`max_iterations` is reached.

### Run Harness Request

| Field | Description |
| ----- | ----------- |
| `repo_path` | Path to the Git repository. |
| `prompt` | Task to execute. |
| `max_iterations` | Maximum generator/reviewer loops. |
| `generator_model` | Model used for generation. |
| `reviewer_model` | Model used for every reviewer skill. |
| `skills` | List of review skills to execute. |

### Run Harness Example

```sh
curl -X POST http://127.0.0.1:8000/run-harness \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/jadraque/Documents/source/looping-louie/web",
    "prompt": "Fix the Nuxt layout warning. Ensure the default layout is actually used by app.vue. Do not redesign the homepage. Keep changes minimal.",
    "max_iterations": 2,
    "generator_model": "zai-org/GLM-5.2",
    "reviewer_model": "gpt-4.1-mini",
    "skills": [
      "small_patch_quality",
      "nuxt_code_review"
    ]
  }'
```

---

## POST /run-tasks

Executes every pending task from a `tasks.json` file.

Tasks are processed sequentially.

For each approved task, Looping Louie:

1. Executes the harness.
2. Commits the repository changes.
3. Marks the task as `done`.
4. Continues with the next pending task.

Execution stops immediately when a task cannot be approved within the
configured iteration limit.

### Run Tasks Request

| Field | Description |
| ----- | ----------- |
| `repo_path` | Path to the Git repository. |
| `tasks_path` | Path to `tasks.json`. |
| `max_iterations` | Maximum iterations per task. |
| `generator_model` | Model used for generation. |
| `reviewer_model` | Model used for every reviewer skill. |
| `skills` | List of review skills executed for every task. |

### Run Tasks Example

```sh
curl -X POST http://127.0.0.1:8000/run-tasks \
  -H "Content-Type: application/json" \
  -d '{
    "repo_path": "/home/jadraque/Documents/source/looping-louie/web",
    "tasks_path": "/home/jadraque/Documents/source/looping-louie/web/.looping-louie/tasks.json",
    "max_iterations": 3,
    "generator_model": "zai-org/GLM-5.2",
    "reviewer_model": "gpt-4.1-mini",
    "skills": [
      "small_patch_quality",
      "nuxt_code_review",
      "preserve_existing_ui"
    ]
  }'
```

---

## Choosing an endpoint

Use **`/run-harness`** when:

- experimenting with prompts;
- testing a new skill;
- implementing one isolated change.

Use **`/run-tasks`** when:

- executing a development backlog;
- evolving a project incrementally;
- generating one commit per logical task.

`/run-tasks` is expected to become the primary production entry point, while
`/run-harness` serves as the reusable building block used internally by
higher-level workflows.

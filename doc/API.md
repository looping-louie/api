# API

Looping Louie API exposes task checkpoint endpoints plus a versioned API for
managing the resources used by the execution runtime.

The API owns planning, generation, and reviewer decisions.
CLI owns local repository execution (filesystem, Git, workspace lifecycle).

- `/api/v1/providers/*` manages model-provider configuration.
- `/api/v1/models/*` exposes the curated model catalog.
- `/api/v1/personas/*` manages persona instructions.
- `/api/v1/skills/*` manages skill instructions.
- `/api/v1/loops/*` manages stored multi-agent loop definitions.
- `/api/v1/pipelines/*` manages ordered loop and human-gate definitions.
- `/api/v1/tasks/start` starts one task run and returns the first checkpoint action.
- `/api/v1/tasks/continue` advances one checkpoint transition.
- `/api/v1/tasks/{run_id}` returns the latest checkpoint state for one run.

---

## Versioned API conventions

All task, provider, model, persona, skill, loop, and pipeline routes use the
`/api/v1` prefix.

These routes require an authenticated user. In local development,
`LOUIE_DEV_AUTH=true` injects `LOUIE_DEV_USER_ID` as that user. A request may
select one of the user's workspaces with the optional `X-Workspace-ID` header.
If the user has access to more than one workspace and the header is omitted,
the API returns `409 workspace_selection_required`.

List operations return an object with `items` and `total`, except
`GET /api/v1/providers`, which returns a JSON array. The optional `search`
query parameter accepted by resource lists is case-insensitive and must contain
between 1 and 200 characters. Loop and loop-changelog lists instead accept a
non-negative `offset` and always return at most ten items. Pipeline lists also
use fixed ten-item pages, support `status` and `search`, and exclude archived
pipelines unless `status=archived` is requested.

Create operations return `201 Created`. Persona and skill content updates use
optimistic concurrency and require the current positive integer
`expected_version`; loop updates do not.
Successful deletes return:

```json
{
  "deleted": true
}
```

Domain errors use this envelope:

```json
{
  "error": {
    "code": "version_conflict",
    "message": "The resource has changed.",
    "details": {
      "expected_version": 1,
      "current_version": 2
    }
  }
}
```

---

## Providers

Provider routes manage encrypted credentials and workspace-specific enablement.
The supported `provider_id` values are `anthropic`, `nvidia`, `ollama`,
`openai`, and `together`.

### Provider calls

| Method   | Path                                      | Description                                                   |
| -------- | ----------------------------------------- | ------------------------------------------------------------- |
| `GET`    | `/api/v1/providers`                       | Lists catalog providers and their workspace state.            |
| `GET`    | `/api/v1/providers/{provider_id}`         | Returns provider metadata and configuration state.            |
| `PATCH`  | `/api/v1/providers/{provider_id}`         | Updates credentials, base URL, or enabled state.              |
| `DELETE` | `/api/v1/providers/{provider_id}`         | Deletes workspace configuration and encrypted credentials.    |

### Patch Provider Request

| Field      | Description                                                            |
| ---------- | ---------------------------------------------------------------------- |
| `api_key`  | New API key. Null clears it when keys are optional; omitted preserves.  |
| `base_url` | Custom base URL. Null restores the catalog default; omitted preserves.  |
| `enabled`  | Enables or disables the workspace configuration.                        |

At least one field must be present. Initial configuration is enabled unless
`enabled` is false. Updated credentials and URLs, and configurations being
enabled, are tested before storage. The API never returns the complete key:
provider responses contain only `key_trimmed`.

### Configure Provider Example

```sh
curl -s -X PATCH http://127.0.0.1:8000/api/v1/providers/openai \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "api_key": "provider-api-key"
  }'
```

Provider GET and PATCH responses contain metadata plus `configured`, `enabled`,
`key_trimmed`, `base_url`, `model_count`, and `model_catalog_note`.

---

## Models

Model routes expose the curated, provider-independent model catalog and compute
availability from the providers configured in the selected workspace.

### Model calls

| Method | Path                                      | Description                                                   |
| ------ | ----------------------------------------- | ------------------------------------------------------------- |
| `GET`  | `/api/v1/models`                          | Lists models, catalog metadata, pricing, and availability.     |
| `GET`  | `/api/v1/models/{model_id}`               | Returns deployments, capabilities, and availability details.  |

### List Models Query

| Parameter            | Description                                                                 |
| -------------------- | --------------------------------------------------------------------------- |
| `provider_id`        | Filters by `anthropic`, `nvidia`, `ollama`, `openai`, or `together`.         |
| `capability`         | Filters by `coding`, `function_calling`, `reasoning`, `structured_output`, `text`, or `vision`. |
| `status`             | Filters by catalog status: `active`, `deprecated`, or `preview`.             |
| `available`          | Filters by effective workspace availability (`true` or `false`).            |
| `search`             | Searches name, vendor, family, and tags; 1–200 characters.                   |
| `include_deprecated` | Includes deprecated entries. Defaults to `false`.                            |

### List Models Example

```sh
curl -s \
  "http://127.0.0.1:8000/api/v1/models?capability=coding&available=true" \
  -H "X-Workspace-ID: workspace-id"
```

List items include summary metadata, capabilities, provider IDs, availability,
starting price, and tags. A describe response additionally includes every
provider deployment, its endpoint and limits, pricing, replacement model, and
workspace-specific availability reason.

---

## Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled, disabled, or used as the source of an editable
custom persona.

### Persona calls

| Method   | Path                                | Description                                                   |
| -------- | ----------------------------------- | ------------------------------------------------------------- |
| `GET`    | `/api/v1/personas`                  | Lists persona metadata without full instructions.             |
| `GET`    | `/api/v1/personas/{persona_id}`     | Returns a persona including its complete instructions.        |
| `POST`   | `/api/v1/personas`                  | Creates a custom persona or copies an available source.       |
| `PATCH`  | `/api/v1/personas/{persona_id}`     | Modifies content or workspace enablement.                     |
| `DELETE` | `/api/v1/personas/{persona_id}`     | Deletes a persona when it has no blocking dependencies.       |

### Create Persona Request

| Field               | Description                                         |
| ------------------- | --------------------------------------------------- |
| `name`              | Required non-empty display name.                    |
| `description`       | Optional description. Defaults to an empty string.  |
| `instructions`      | Required non-empty complete persona instructions.   |
| `skill_ids`         | Ordered IDs of skills associated with the persona.   |
| `metadata`          | Optional JSON object. Defaults to `{}`.             |
| `source_persona_id` | Omit when creating a persona from supplied content. |

To copy an available, non-deprecated persona, send `source_persona_id` and an
optional `name`. The source description, instructions, skills, and metadata are
copied. Do not include those copied fields in the request. If `name` is omitted,
it defaults to the source name followed by ` Copy`.

### Patch Persona Request

Include at least one of `name`, `description`, `instructions`, `skill_ids`,
`metadata`, or `enabled`. Supplying `skill_ids` replaces the complete
association; an empty list removes every skill. Content changes require
`expected_version`; an enabled-only change does not. `enabled` must be `true`
or `false`, not `null`. Built-in content is immutable, but its enabled state
can be patched.

### Create Persona Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "API reviewer",
    "description": "Reviews public API compatibility.",
    "instructions": "Inspect every public contract and report breaking changes.",
    "skill_ids": ["builtin:skill:security"],
    "metadata": {
      "team": "platform"
    }
  }'
```

To create a copy instead:

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/personas \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "source_persona_id": "builtin:persona:tech_lead",
    "name": "Platform lead"
  }'
```

Write and get operations return the complete persona, including `id`,
instructions, `skill_ids`, metadata, origin and capabilities, version, and
timestamps. Deleting a custom skill automatically removes its ID from every
associated persona. List items omit instructions, skill IDs, and metadata.

---

## Skills

A skill is a reusable review or deliberation instruction. Built-in skills are
immutable; they can be enabled, disabled, or used as the source of an editable
custom skill.

### Skill calls

| Method   | Path                            | Description                                               |
| -------- | ------------------------------- | --------------------------------------------------------- |
| `GET`    | `/api/v1/skills`                | Lists skill metadata without full instructions.           |
| `GET`    | `/api/v1/skills/{skill_id}`     | Returns a skill including its complete instructions.      |
| `POST`   | `/api/v1/skills`                | Creates a custom skill or copies an available source.     |
| `PATCH`  | `/api/v1/skills/{skill_id}`     | Modifies content or workspace enablement.                 |
| `DELETE` | `/api/v1/skills/{skill_id}`     | Deletes a skill when it has no blocking dependencies.     |

### Create Skill Request

| Field             | Description                                                   |
| ----------------- | ------------------------------------------------------------- |
| `name`            | Required non-empty display name.                              |
| `description`     | Optional description. Defaults to an empty string.            |
| `instructions`    | Required non-empty complete skill instructions.               |
| `metadata`        | Optional skill metadata. Defaults to `{}`.                    |
| `source_skill_id` | Omit when creating a skill from supplied content.             |

Skill metadata may contain `applies_when`, a non-empty list of strings, and
`default_strictness`. Strictness values are integers from 0 to 100 keyed by
`prototype`, `mvp`, and `production`. Extra metadata fields are allowed.

To copy an available, non-deprecated skill, send `source_skill_id` and an
optional `name`. The source description, instructions, and metadata are copied.
Do not include those copied fields in the request. If `name` is omitted, it
defaults to the source name followed by ` Copy`.

### Patch Skill Request

Include at least one of `name`, `description`, `instructions`, `metadata`, or
`enabled`. Content changes require `expected_version`; an enabled-only change
does not. `enabled` must be `true` or `false`, not `null`. Built-in content is
immutable, but its enabled state can be patched.

### Create Skill Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "API compatibility",
    "description": "Detects breaking API changes.",
    "instructions": "Compare routes and schemas with the documented contract.",
    "metadata": {
      "applies_when": ["An HTTP contract changes"],
      "default_strictness": {
        "production": 100
      }
    }
  }'
```

To create a copy instead:

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/skills \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "source_skill_id": "builtin:skill:api_compatibility",
    "name": "Platform API compatibility"
  }'
```

Write and get operations return the complete skill, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.

---

## Loops

A loop stores a validated flow, its model/persona agents, stop conditions, and
the expected output. The API stores this definition but does not execute it.

### Loop calls

| Method   | Path                                      | Description                                                   |
| -------- | ----------------------------------------- | ------------------------------------------------------------- |
| `GET`    | `/api/v1/loops`                           | Lists up to ten complete loop definitions.                    |
| `POST`   | `/api/v1/loops`                           | Creates an active loop.                                       |
| `GET`    | `/api/v1/loops/{loop_id}`                 | Returns one complete loop.                                    |
| `PATCH`  | `/api/v1/loops/{loop_id}`                 | Updates supplied mutable fields or changes status.            |
| `DELETE` | `/api/v1/loops/{loop_id}`                 | Permanently deletes a loop while retaining its changelog.     |
| `GET`    | `/api/v1/loops/{loop_id}/changelog`       | Lists up to ten newest immutable changelog entries.           |

### Create Loop Request

| Field              | Description                                                       |
| ------------------ | ----------------------------------------------------------------- |
| `title`            | Required non-empty display title.                                 |
| `description`      | Required description.                                             |
| `flow`             | `direct`, `refinement`, or `roundtable`.                           |
| `stop_conditions`  | At least one positive supported stop condition.                   |
| `agents`           | Flow-compatible model, persona, and role assignments.             |
| `output_contract`  | Generic `text`, `json`, or `files` output description.            |

Agents require `model_id`, `persona_id`, and a `generator`, `reviewer`, or
`aggregator` role. Their `id` is optional and generated when omitted. Agents do
not accept skills. `direct` requires at least one agent and at most one
aggregator. `refinement` requires exactly one generator and at least one
reviewer. `roundtable` requires at least two generators and exactly one
aggregator.

`stop_conditions` supports optional positive `max_iterations`, `max_tokens`,
and `timeout_seconds` values, with at least one configured. A `files` output
requires at least one path; a `json` output requires a JSON object in `schema`.

### Create Loop Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/loops \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "title": "Implementation loop",
    "description": "One generator with an independent reviewer.",
    "flow": "refinement",
    "stop_conditions": {
      "max_iterations": 3,
      "max_tokens": 50000
    },
    "agents": [
      {
        "model_id": "gpt-5.6-terra",
        "persona_id": "builtin:persona:tech_lead",
        "role": "generator"
      },
      {
        "model_id": "kimi-k2.6",
        "persona_id": "builtin:persona:devils_advocate",
        "role": "reviewer"
      }
    ],
    "output_contract": {
      "type": "files",
      "description": "Produce the implementation plan.",
      "files": ["plan.md"]
    }
  }'
```

The API generates the loop ID, missing agent IDs, `active` status, timestamps,
and actor fields. PATCH replaces the complete agent array when supplied,
preserves omitted fields, and rejects empty or ineffective changes. An archived
loop is immutable except for a status-only reactivation to `active`.

Every create, update, status transition, and delete writes an immutable
changelog entry in the same transaction. Creation and deletion entries contain
the complete loop representation; update entries contain only changed fields.
The changelog remains available after deletion.

Every workspace initially receives two ordinary, active catalog loops:
`shape ideas`, which produces `ideas.md`, and `plan implementation`, which
produces `tasks.json`. All their agents use `deepseek-v4-pro`. Installation is
performed only once per workspace, so either loop can subsequently be modified
or deleted without being reset or recreated.

---

## Pipelines

A pipeline stores an ordered sequence of loop references and human checkpoints.
The API manages and validates the definition but does not execute it.

### Pipeline calls

| Method   | Path                                        | Description                                   |
| -------- | ------------------------------------------- | --------------------------------------------- |
| `GET`    | `/api/v1/pipelines`                         | Lists ten filtered pipelines after an offset. |
| `POST`   | `/api/v1/pipelines`                         | Creates an enabled pipeline.                  |
| `GET`    | `/api/v1/pipelines/{pipeline_id}`           | Returns one complete ordered definition.      |
| `PATCH`  | `/api/v1/pipelines/{pipeline_id}`           | Updates mutable fields or enablement.          |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}`           | Archives the pipeline.                        |
| `GET`    | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries.            |

Creation requires a non-empty `title`, a `description`, and at least two
steps. New pipelines are enabled. PATCH accepts `title`, `description`,
`enabled`, and `steps`; supplying `steps` replaces the complete ordered array.
Archived pipelines are immutable and omitted from unfiltered listings.

The list accepts a non-negative `offset`, optional case-insensitive `search`
over title and description, and optional `status` of `active`, `disabled`, or
`archived`. Active pipelines sort before disabled and archived pipelines.

### Pipeline steps

Loop steps contain only an active loop reference:

```json
{
  "type": "loop",
  "loop_id": "loop-id"
}
```

Approval gates need no configuration:

```json
{
  "type": "human_gate",
  "gate_type": "approval"
}
```

Quiz gates require `config` and `minimum_correct_answers`.
`question_count` defaults to `10` and `option_count` defaults to `3`:

```json
{
  "type": "human_gate",
  "gate_type": "quiz",
  "config": {
    "minimum_correct_answers": 8,
    "question_count": 10,
    "option_count": 3
  }
}
```

Counts must be positive, `option_count` must be at least two, and
`minimum_correct_answers` cannot exceed `question_count`. Approval gates reject
`config`; pipeline definitions never store generated quiz questions or answers.
Repeated loop references and repeated human gates are allowed.

Every create, patch, enablement change, and archival appends a changelog entry
in the same transaction. Step diffs report additions, removals, positional
changes, and order changes.

Request schema failures use the standard API error envelope. Pipeline step
discriminator failures use `unsupported_pipeline_step`, human-gate
discriminator failures use `unsupported_human_gate_type`, and other invalid
step structures use `invalid_pipeline_steps`.

---

## POST /api/v1/tasks/start

Starts checkpoint-based task execution.

The API returns `status=in_progress` with `next_action=collect_snapshot` and
an opaque `continuation_token`.

## POST /api/v1/tasks/continue

Advances one checkpoint transition for an existing task run.

The CLI must send:

- `run_id`
- `continuation_token`
- `idempotency_key`
- `action_result`

The API returns the next action or a terminal state.

## GET /api/v1/tasks/{run_id}

Returns the latest checkpoint state for one task run identifier.

---

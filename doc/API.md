# API

Looping Louie API exposes task checkpoint and meeting endpoints, plus a
versioned API for managing the resources used by the execution runtime.

The API owns planning, generation, and reviewer decisions.
CLI owns local repository execution (filesystem, Git, workspace lifecycle).

- `/api/v1/providers/*` manages model-provider configuration.
- `/api/v1/models/*` exposes the curated model catalog.
- `/api/v1/personas/*` manages persona instructions.
- `/api/v1/skills/*` manages skill instructions.
- `/api/v1/loops/*` manages stored multi-agent loop definitions.
- `/task/start` starts one task run and returns the first checkpoint action.
- `/task/continue` advances one checkpoint transition.
- `/task/{run_id}` returns the latest checkpoint state for one run.
- `/meeting/run` runs a discussion between several personas to shape an idea
  or produce an implementation plan.

---

## Versioned API conventions

All provider, model, persona, skill, and loop routes use the
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
non-negative `offset` and always return at most ten items.

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

---

## POST /task/start

Starts checkpoint-based task execution.

The API returns `status=in_progress` with `next_action=collect_snapshot` and
an opaque `continuation_token`.

## POST /task/continue

Advances one checkpoint transition for an existing task run.

The CLI must send:

- `run_id`
- `continuation_token`
- `idempotency_key`
- `action_result`

The API returns the next action or a terminal state.

## GET /task/{run_id}

Returns the latest checkpoint state for one task run identifier.

---

## POST /meeting/run — Shape Idea

Executes a structured multi-persona meeting that transforms an initial idea into
a concise and decision-ready `idea.md` document.

The meeting planner assigns skills to the requested personas and divides them
between participants and challengers.

During each round, Looping Louie:

1. Asks the facilitator to define the round objective.
2. Executes participant contributions in parallel.
3. Consolidates agreements and disagreements.
4. Generates a complete candidate artifact.
5. Runs the challengers in parallel.
6. Validates the artifact structure and content.
7. Continues until approval or the configured round limit is reached.

The resulting document follows the standard idea structure and is limited to
1,000 words.

### Shape Idea Request

| Field               | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `meeting_type`      | Meeting preset. Must be `shape_idea`.                        |
| `prompt`            | Initial idea or problem to shape.                            |
| `max_iterations`    | Maximum number of contribution rounds. Defaults to `3`.      |
| `participant_model` | Model used for participant contributions.                    |
| `challenger_model`  | Model used by challengers and the validator.                 |
| `synthesizer_model` | Model used to write the complete artifact.                   |
| `planner_model`     | Model used by the meeting planner and facilitator.           |
| `required_personas` | Personas that must participate in the meeting.               |
| `required_skills`   | Skills that must be assigned to participants or challengers. |
| `constitution`      | Optional project principles and constraints.                 |

### Shape Idea Example

```sh
curl -s -X POST http://127.0.0.1:8000/meeting/run \
  -H "Content-Type: application/json" \
  -d '{
    "meeting_type": "shape_idea",
    "prompt": "Quiero crear una funcionalidad para que equipos debatan ideas con varias personas y skills antes de convertirlas en tareas de implementación.",
    "max_iterations": 3,
    "participant_model": "zai-org/GLM-5.2",
    "challenger_model": "gpt-4.1-mini",
    "synthesizer_model": "gpt-4.1-mini",
    "planner_model": "gpt-4.1-mini",
    "required_personas": [
      "product_manager",
      "ux_designer",
      "tech_lead",
      "devils_advocate"
    ],
    "required_skills": [
      "idea_shaping",
      "customer_problem",
      "risk_analysis"
    ],
    "constitution": ""
  }' |
jq -r '.final_output' > idea.md
```

The complete API response includes the final artifact, approval state, meeting
trace, and aggregated model metrics.

---

## POST /meeting/run — Plan Implementation

Executes a structured multi-persona meeting that transforms an approved
`idea.md` document into an ordered `tasks.json` implementation backlog.

The complete contents of `idea.md` are sent inside the `prompt` field.

Each generated task:

1. Has a unique sequential identifier.
2. Starts with the `pending` status.
3. Contains a self-contained implementation prompt.
4. Preserves the approved scope and non-goals.
5. Includes sufficient acceptance criteria.
6. Produces one small and coherent commit.
7. Depends only on repository state or earlier tasks.

### Plan Implementation Request

| Field               | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `meeting_type`      | Meeting preset. Must be `plan_implementation`.               |
| `prompt`            | Complete contents of the approved `idea.md` document.        |
| `max_iterations`    | Maximum number of contribution rounds. Defaults to `3`.      |
| `participant_model` | Model used for participant contributions.                    |
| `challenger_model`  | Model used by challengers and the validator.                 |
| `synthesizer_model` | Model used to generate the final `tasks.json`.               |
| `planner_model`     | Model used by the meeting planner and facilitator.           |
| `required_personas` | Personas that must participate in the meeting.               |
| `required_skills`   | Skills that must be assigned to participants or challengers. |
| `constitution`      | Optional project principles and constraints.                 |

### Plan Implementation Example

```sh
jq -Rs '{
  meeting_type: "plan_implementation",
  prompt: (the content of idea.md, for instance),
  max_iterations: 3,
  participant_model: "zai-org/GLM-5.2",
  challenger_model: "gpt-4.1-mini",
  synthesizer_model: "gpt-4.1-mini",
  planner_model: "gpt-4.1-mini",
  required_personas: [
    "product_manager",
    "tech_lead",
    "ux_designer",
    "devils_advocate"
  ],
  required_skills: [
    "task_decomposition",
    "acceptance_criteria",
    "risk_analysis",
    "resilience"
  ],
  constitution: ""
}' idea.md |
curl -s -X POST http://127.0.0.1:8000/meeting/run \
  -H "Content-Type: application/json" \
  --data-binary @- |
jq -r '.final_output' > tasks.json
```

The generated file contains a JSON array with this task structure:

```json
{
  "id": "ideas-001",
  "status": "pending",
  "prompt": "Self-contained implementation instruction with acceptance criteria.",
  "run_id": "",
  "commit_message": "Add ideas empty state"
}
```

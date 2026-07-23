# API

Looping Louie API exposes task checkpoint and meeting endpoints, plus a
versioned API for managing the resources used by the execution runtime.

The API owns planning, generation, and reviewer decisions.
CLI owns local repository execution (filesystem, Git, workspace lifecycle).

- `/api/v1/providers/*` manages model-provider configuration.
- `/api/v1/models/*` exposes the curated model catalog.
- `/api/v1/personas/*` manages persona instructions.
- `/api/v1/skills/*` manages skill instructions.
- `/api/v1/councils/*` manages persona and skill compositions.
- `/api/v1/loops/*` manages executable council and model configurations.
- `/task/start` starts one task run and returns the first checkpoint action.
- `/task/continue` advances one checkpoint transition.
- `/task/{run_id}` returns the latest checkpoint state for one run.
- `/meeting/run` runs a discussion between several personas to shape an idea
  or produce an implementation plan.

---

## Versioned API conventions

All provider, model, persona, skill, council, and loop routes use the
`/api/v1` prefix.

These routes require an authenticated user. In local development,
`LOUIE_DEV_AUTH=true` injects `LOUIE_DEV_USER_ID` as that user. A request may
select one of the user's workspaces with the optional `X-Workspace-ID` header.
If the user has access to more than one workspace and the header is omitted,
the API returns `409 workspace_selection_required`.

List operations return an object with `items` and `total`, except
`GET /api/v1/providers/list`, which returns a JSON array. The optional `search`
query parameter accepted by resource lists is case-insensitive and must contain
between 1 and 200 characters.

Create operations return `201 Created`. Updates use optimistic concurrency:
the request must include the current positive integer `expected_version`.
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

| Method   | Path                                              | Description                                                        |
| -------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| `GET`    | `/api/v1/providers/list`                          | Lists supported providers and their state in the workspace.        |
| `GET`    | `/api/v1/providers/describe/{provider_id}`        | Returns one provider's metadata and configuration state.           |
| `POST`   | `/api/v1/providers/configure/{provider_id}`       | Stores or replaces credentials and an optional base URL.           |
| `POST`   | `/api/v1/providers/enable/{provider_id}`          | Enables a previously configured provider.                          |
| `POST`   | `/api/v1/providers/disable/{provider_id}`         | Disables a provider without deleting its credentials.              |
| `POST`   | `/api/v1/providers/test/{provider_id}`            | Tests the stored provider configuration.                           |
| `DELETE` | `/api/v1/providers/delete/{provider_id}`          | Deletes the stored configuration and encrypted credentials.        |

### Configure Provider Request

| Field      | Description                                                        |
| ---------- | ------------------------------------------------------------------ |
| `api_key`  | Optional non-empty API key. It may be omitted for Ollama.           |
| `base_url` | Optional non-empty custom API base URL.                             |

At least the values required by the selected provider must be present. The API
never returns the complete key: provider responses contain only `key_trimmed`.

### Configure Provider Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/providers/configure/openai \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "api_key": "provider-api-key"
  }'
```

`list`, `describe`, `configure`, `enable`, and `disable` return provider
metadata and the fields `configured`, `enabled`, `key_trimmed`, `base_url`,
`model_count`, and `model_catalog_note`. `test` returns `provider`, `success`,
`message`, and `latency_ms`.

---

## Models

Model routes expose the curated, provider-independent model catalog and compute
availability from the providers configured in the selected workspace.

### Model calls

| Method | Path                                      | Description                                                   |
| ------ | ----------------------------------------- | ------------------------------------------------------------- |
| `GET`  | `/api/v1/models/list`                     | Lists models, catalog metadata, pricing, and availability.     |
| `GET`  | `/api/v1/models/describe/{model_id}`      | Returns deployments, capabilities, and availability details.  |

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
  "http://127.0.0.1:8000/api/v1/models/list?capability=coding&available=true" \
  -H "X-Workspace-ID: workspace-id"
```

List items include summary metadata, capabilities, provider IDs, availability,
starting price, and tags. A describe response additionally includes every
provider deployment, its endpoint and limits, pricing, replacement model, and
workspace-specific availability reason.

---

## Personas

A persona is a reusable set of agent instructions. Built-in personas are
immutable; they can be enabled, disabled, or duplicated into editable custom
personas.

### Persona calls

| Method   | Path                                               | Description                                                       |
| -------- | -------------------------------------------------- | ----------------------------------------------------------------- |
| `GET`    | `/api/v1/personas/list`                            | Lists persona metadata without full instructions.                 |
| `GET`    | `/api/v1/personas/describe/{persona_id}`           | Returns a persona including its complete instructions.            |
| `POST`   | `/api/v1/personas/create`                          | Creates a custom persona in the selected workspace.               |
| `POST`   | `/api/v1/personas/update/{persona_id}`             | Updates an editable persona.                                      |
| `PUT`    | `/api/v1/personas/{persona_id}/enabled`            | Enables or disables an available persona in the workspace.        |
| `POST`   | `/api/v1/personas/{persona_id}/duplicate`          | Duplicates an available persona as an editable custom persona.     |
| `DELETE` | `/api/v1/personas/delete/{persona_id}`             | Deletes a persona when it has no blocking dependencies.           |

### Create Persona Request

| Field          | Description                                      |
| -------------- | ------------------------------------------------ |
| `name`         | Required non-empty display name.                 |
| `description`  | Optional description. Defaults to an empty string. |
| `instructions` | Required non-empty complete persona instructions. |
| `metadata`     | Optional JSON object. Defaults to `{}`.           |

### Update Persona Request

`expected_version` is required. Include at least one of `name`, `description`,
`instructions`, or `metadata`.

### Enable and Duplicate Persona Requests

The enablement body is `{"enabled": true}` or `{"enabled": false}`. The
duplicate body may be `{}` or contain a non-empty `name` override.

### Create Persona Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/personas/create \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "API reviewer",
    "description": "Reviews public API compatibility.",
    "instructions": "Inspect every public contract and report breaking changes.",
    "metadata": {
      "team": "platform"
    }
  }'
```

Write and describe operations return the complete persona, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.

---

## Skills

A skill is a reusable review or deliberation instruction. Built-in skills are
immutable; they can be enabled, disabled, or duplicated into editable custom
skills.

### Skill calls

| Method   | Path                                           | Description                                                     |
| -------- | ---------------------------------------------- | --------------------------------------------------------------- |
| `GET`    | `/api/v1/skills/list`                          | Lists skill metadata without full instructions.                 |
| `GET`    | `/api/v1/skills/describe/{skill_id}`           | Returns a skill including its complete instructions.            |
| `POST`   | `/api/v1/skills/create`                        | Creates a custom skill in the selected workspace.               |
| `POST`   | `/api/v1/skills/update/{skill_id}`             | Updates an editable skill.                                      |
| `PUT`    | `/api/v1/skills/{skill_id}/enabled`            | Enables or disables an available skill in the workspace.        |
| `POST`   | `/api/v1/skills/{skill_id}/duplicate`          | Duplicates an available skill as an editable custom skill.       |
| `DELETE` | `/api/v1/skills/delete/{skill_id}`             | Deletes a skill when it has no blocking dependencies.           |

### Create Skill Request

| Field          | Description                                                       |
| -------------- | ----------------------------------------------------------------- |
| `name`         | Required non-empty display name.                                  |
| `description`  | Optional description. Defaults to an empty string.                |
| `instructions` | Required non-empty complete skill instructions.                   |
| `metadata`     | Optional skill metadata. Defaults to `{}`.                         |

Skill metadata may contain `applies_when`, a non-empty list of strings, and
`default_strictness`. Strictness values are integers from 0 to 100 keyed by
`prototype`, `mvp`, and `production`. Extra metadata fields are allowed.

### Update Skill Request

`expected_version` is required. Include at least one of `name`, `description`,
`instructions`, or `metadata`.

### Enable and Duplicate Skill Requests

The enablement body is `{"enabled": true}` or `{"enabled": false}`. The
duplicate body may be `{}` or contain a non-empty `name` override.

### Create Skill Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/skills/create \
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

Write and describe operations return the complete skill, including `id`,
instructions, metadata, origin and capabilities, version, and timestamps. List
items omit instructions and metadata.

---

## Councils

A council assigns one persona and one or more skills to each role used during a
meeting or loop.

### Council calls

| Method   | Path                                             | Description                                                  |
| -------- | ------------------------------------------------ | ------------------------------------------------------------ |
| `GET`    | `/api/v1/councils/list`                          | Lists council metadata without expanding assignments.        |
| `GET`    | `/api/v1/councils/describe/{council_id}`         | Returns the council and all role assignments.                 |
| `POST`   | `/api/v1/councils/create`                        | Creates a council.                                           |
| `POST`   | `/api/v1/councils/update/{council_id}`           | Updates metadata or replaces assignments.                    |
| `DELETE` | `/api/v1/councils/delete/{council_id}`           | Deletes a council when no loop depends on it.                 |

### Create Council Request

| Field         | Description                                                   |
| ------------- | ------------------------------------------------------------- |
| `name`        | Required non-empty display name.                              |
| `description` | Optional description. Defaults to an empty string.            |
| `assignments` | Required non-empty array of role assignments.                 |

Each assignment contains a non-empty `role`, a `persona_id`, and a non-empty
`skill_ids` array. Referenced personas and skills must exist and be enabled.

### Update Council Request

`expected_version` is required. Include at least one of `name`, `description`,
or `assignments`. When supplied, `assignments` replaces the complete assignment
list.

### Create Council Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/councils/create \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "Implementation council",
    "description": "Generates and reviews implementation changes.",
    "assignments": [
      {
        "role": "generator",
        "persona_id": "builtin:persona:tech_lead",
        "skill_ids": ["builtin:skill:web_development"]
      }
    ]
  }'
```

Describe and write operations return assignments, version, and timestamps.
List items replace assignments with `item_count`.

---

## Loops

A loop binds a council's roles to models and defines the maximum number of
iterations.

### Loop calls

| Method   | Path                                      | Description                                                       |
| -------- | ----------------------------------------- | ----------------------------------------------------------------- |
| `GET`    | `/api/v1/loops/list`                      | Lists loop metadata and configuration summaries.                  |
| `GET`    | `/api/v1/loops/describe/{loop_id}`       | Returns council, model bindings, and iteration limit.              |
| `POST`   | `/api/v1/loops/create`                   | Creates a loop.                                                   |
| `POST`   | `/api/v1/loops/update/{loop_id}`         | Updates loop metadata or configuration.                           |
| `DELETE` | `/api/v1/loops/delete/{loop_id}`         | Deletes a loop without deleting historical run snapshots.         |
| `POST`   | `/api/v1/loops/validate/{loop_id}`       | Validates council roles and model references for a stored loop.    |

### Create Loop Request

| Field            | Description                                                   |
| ---------------- | ------------------------------------------------------------- |
| `name`           | Required non-empty display name.                              |
| `description`    | Optional description. Defaults to an empty string.            |
| `council_id`     | Required identifier of an existing council.                   |
| `max_iterations` | Required positive integer.                                    |
| `model_bindings` | Required non-empty array assigning a model to each role.      |

Each model binding contains a non-empty `role` and `model_id`. Referenced
models must exist, be available in the workspace, and cover the council roles.

### Update Loop Request

`expected_version` is required. Include at least one of `name`, `description`,
`council_id`, `max_iterations`, or `model_bindings`. When supplied,
`model_bindings` replaces the complete binding list.

### Create Loop Example

```sh
curl -s -X POST http://127.0.0.1:8000/api/v1/loops/create \
  -H "Content-Type: application/json" \
  -H "X-Workspace-ID: workspace-id" \
  -d '{
    "name": "Implementation loop",
    "description": "One generator with an independent reviewer.",
    "council_id": "council-id",
    "max_iterations": 3,
    "model_bindings": [
      {
        "role": "generator",
        "model_id": "gpt-5.6-terra"
      }
    ]
  }'
```

Describe and write operations return the complete configuration, version, and
timestamps. List items replace model bindings with `item_count`. A successful
validation returns `{"valid": true, "loop": {...}}`; invalid configurations use
the standard error envelope.

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

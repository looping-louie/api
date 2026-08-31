# Activities

Standalone Activities are User-owned, reusable definitions of work. An
Activity has a name, description, status, type-specific configuration, audit
history, and an immutable type. Activities can be created directly or supplied
inline when a Pipeline is created or updated. Pipeline-created Activities keep
their Pipeline Workspace as provenance for internal step resolution, while
standalone Activities have no Workspace association.

The API selects the configuration shape from the top-level `type` field. The
`config` object does not include its own type discriminator. Activity statuses
are `active`, `disabled`, and `archived`.

## Activity Categories

| Category | Activity type | Purpose | Activity runs |
| -------- | ------------- | ------- | ------------- |
| Loop | `direct_loop` | Produce one model-generated operation plan. | Supported |
| Loop | `refinement_loop` | Run an iterative generator and reviewer flow. | Supported |
| Loop | `roundtable_loop` | Synthesize proposals from multiple generators. | Supported |
| Human | `approval` | Represent a human approval decision. | Supported |
| Human | `quiz` | Collect a human quiz response. | Supported |

## Loop Activities

Loop Activities configure one or more model agents, stop conditions, and an
output contract. An agent combines a Persona and one role. The Persona's
instructions are combined with the agent's explicit `model_id` during
generation.

- `generator`: produces a candidate solution or proposed output;
- `reviewer`: evaluates a candidate and provides feedback for refinement;
- `aggregator`: synthesizes multiple proposals into a consolidated result.

The role cardinality is part of every loop Activity's configuration contract.

| Type of loop | Number of generators | Number of reviewers | Number of aggregators |
| ------------ | -------------------- | ------------------- | --------------------- |
| Direct | Exactly 1 | 0 | 0 |
| Refinement | Exactly 1 | At least 1 | 0 |
| Roundtable | At least 2 | 0 | Exactly 1 |

### Direct Loop

A `direct_loop` is an executable single-agent task. Its one generator returns
a JSON operation plan that the CLI applies at its repository and Git
checkpoints. It does not allow reviewer or aggregator agents.

### Refinement Loop

A `refinement_loop` stores a multi-pass improvement definition. It requires one
generator and one or more reviewers, without an aggregator. It creates a plan,
collects reviewer approval after local application, and retries from a fresh
repository snapshot when reviewers reject the change within `max_iterations`.

### Roundtable Loop

A `roundtable_loop` is an executable multi-agent task. Each generator produces
a proposal, then the aggregator synthesizes those proposals into the final JSON
operation plan. Reviewers are not allowed. The CLI applies only the
aggregator's final plan, not the individual proposals.

## Human Activities

Human Activities represent decisions or responses that require a person rather
than model execution. They create regular persisted Activity runs with the
`human` executor, `awaiting_human_decision` state, and
`submit_human_decision` continuation action.

### Approval

An `approval` Activity represents a human approval decision. Its configuration
has no additional fields.

### Quiz

A `quiz` Activity collects a human quiz response. Its configuration requires a
`quiz` object that carries the quiz definition.

## Activity Runs

Activities expose persisted runs. Each run identifies its owning Activity by
`activity_id`; it does not expose a legacy loop identifier. A Pipeline-run
freezes an effective Harness for every runtime-executable child Activity-run,
preferring Activity, Pipeline, then User scope. The `louie` Harness is
the compatibility default. PipelineRun creation also freezes agent model
selections, preferring agent, Activity, Pipeline, then User scope. Only
an effective model can generate a model request; `codex_cli` stores it as the
immutable `requested_model`, while Personas provide instructions only. Human
Activities use the built-in `human`
execution mode and submit a terminal decision checkpoint; they do not execute
through a Harness.

An Activity defines logical work rather than a machine-specific executor. A
Pipeline selects the Harness so the same reusable Activity runs through the
API-directed `louie` Harness. Future compatible local coding-agent Harnesses,
such as `codex_cli`, use the same Pipeline-level selection boundary.

## Related Files

- `src/app/models/activity.py` defines the Activity domain model;
- `src/app/schemas/activity.py` validates Activity HTTP contracts;
- `src/app/services/activity_runs/service.py` creates supported Activity runs;
- `src/app/services/activity_runs/generation.py` executes loop Activity runs;
- `doc/endpoints/activities.md` documents the Activity REST API.

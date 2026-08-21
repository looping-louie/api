# Activities

Activities are workspace-scoped, reusable definitions of work. An Activity has
a name, description, status, type-specific configuration, audit history, and an
immutable type. Activities can be created directly or supplied inline when a
Pipeline is created or updated.

The API selects the configuration shape from the top-level `type` field. The
`config` object does not include its own type discriminator. Activity statuses
are `active`, `disabled`, and `archived`.

## Activity Categories

| Category | Activity type | Purpose | Activity runs |
| --- | --- | --- | --- |
| Loop | `direct_loop` | Produce one model-generated operation plan. | Supported |
| Loop | `refinement_loop` | Run an iterative generator and reviewer flow. | Supported |
| Loop | `roundtable_loop` | Synthesize proposals from multiple generators. | Supported |
| Human | `approval` | Represent a human approval decision. | Supported |
| Human | `quiz` | Collect a human quiz response. | Supported |

## Loop Activities

Loop Activities configure one or more model agents, stop conditions, and an
output contract. An agent combines a Persona and one role with either a legacy
model ID or that Persona's linked-service model selection. A selection-only
agent requires a Persona visible in the Activity workspace.

- `generator`: produces a candidate solution or proposed output;
- `reviewer`: evaluates a candidate and provides feedback for refinement;
- `aggregator`: synthesizes multiple proposals into a consolidated result.

The role cardinality is part of every loop Activity's configuration contract.

| Type of loop | Number of generators | Number of reviewers | Number of aggregators |
| --- | --- | --- | --- |
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
`activity_id`; it does not expose a legacy loop identifier. Runtime executors
resolve configured agent personas from the instruction library before invoking
their models, while human executors submit a terminal decision checkpoint.

## Related Files

- `src/app/models/activity.py` defines the Activity domain model;
- `src/app/schemas/activity.py` validates Activity HTTP contracts;
- `src/app/services/activity_runs/service.py` creates supported Activity runs;
- `src/app/services/activity_runs/generation.py` executes loop Activity runs;
- `doc/endpoints/activities.md` documents the Activity REST API.

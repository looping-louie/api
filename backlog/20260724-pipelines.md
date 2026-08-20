Implement the new `/api/v1/pipelines` resource.

## Goal

A pipeline defines an ordered sequence of loops and human gates.

A valid pipeline must contain at least two steps. Pipelines with zero or one step must be rejected.

This task covers only pipeline definition and management. Do not implement pipeline execution or pipeline runs yet.

## Pipeline model

Create a pipeline entity with:

```json
{
  "id": "pipeline_id",
  "title": "Code implementation pipeline",
  "description": "Implements and validates a task",
  "enabled": true,
  "steps": [],
  "created_at": "...",
  "updated_at": "..."
}
```

Use `title`, not `name`, for consistency with the existing resources.

The order of the `steps` array defines execution order.

Steps do not need IDs. Do not require step IDs to be present or unique.

## Supported step types

Initially support:

* `loop`
* `human_gate`

Use a discriminated union based on the `type` field.

### Loop step

```json
{
  "type": "loop",
  "loop_id": "existing_loop_id"
}
```

Rules:

* `loop_id` is required.
* Validate that the referenced loop exists.
* Do not duplicate the loop configuration inside the pipeline.
* The pipeline only stores the loop reference.

### Approval human gate

```json
{
  "type": "human_gate",
  "gate_type": "approval"
}
```

This represents a human checkpoint where the user only needs to approve continuation.

No additional configuration is required for the MVP.

Replace the quiz human gate definition with:

### Quiz human gate

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

The `config` object is required for quiz gates but its fields have defaults:

* `question_count`: defaults to `10`.
* `option_count`: defaults to `3`.
* `minimum_correct_answers`: defaults to `5`.

Validation rules:

* `question_count` must be at least `1`.
* `option_count` must be at least `2`.
* `minimum_correct_answers` must be at least `1`.
* `minimum_correct_answers` cannot exceed `question_count`.
* `config` must not be accepted for approval gates.
* Quiz questions and answers must not be stored in the pipeline definition.

The model will use this configuration during future pipeline execution to generate:

* The configured number of questions.
* The configured number of answer options per question.
* Exactly one correct option per question.

Example pipeline creation request:

```json
{
  "title": "Implementation with knowledge validation",
  "description": "Runs implementation and checks user understanding",
  "steps": [
    {
      "type": "loop",
      "loop_id": "implementation"
    },
    {
      "type": "human_gate",
      "gate_type": "quiz",
      "config": {
        "minimum_correct_answers": 8,
        "question_count": 10,
        "option_count": 3
      }
    }
  ]
}
```

Add tests covering:

* Default `question_count`.
* Default `option_count`.
* Required `minimum_correct_answers`.
* Minimum correct answers exceeding the question count.
* Invalid zero or negative values.
* Quiz configuration preservation.
* Rejection of quiz configuration in approval gates.


## Pipeline validation

A pipeline must:

* Contain at least two steps.
* Contain only supported step types.
* Reference existing loops.
* Use only `approval` or `quiz` as `gate_type`.
* Preserve the order supplied in the `steps` array.

A pipeline may contain:

* Multiple loop steps.
* Multiple human gates.
* Consecutive loops.
* Consecutive human gates.
* Repeated references to the same loop.

Do not require a pipeline to contain a human gate.

Do not require step identifiers.

Reject unknown fields inside step definitions according to the validation conventions already used by the API.

## Endpoints

Implement:

```text
GET    /api/v1/pipelines
POST   /api/v1/pipelines
GET    /api/v1/pipelines/{pipeline_id}
PATCH  /api/v1/pipelines/{pipeline_id}
DELETE /api/v1/pipelines/{pipeline_id}
```

### Create pipeline

```text
POST /api/v1/pipelines
```

Example request:

```json
{
  "title": "Implementation with knowledge validation",
  "description": "Runs implementation and checks user understanding",
  "steps": [
    {
      "type": "loop",
      "loop_id": "implementation"
    },
    {
      "type": "human_gate",
      "gate_type": "quiz"
    }
  ]
}
```

Validate the complete pipeline before storing it.

### List pipelines

```text
GET /api/v1/pipelines
```

Follow the existing API conventions for:

* Pagination.
* Filtering.
* Archived resources.
* Response envelopes.

Do not return archived pipelines by default.

### Retrieve pipeline

```text
GET /api/v1/pipelines/{pipeline_id}
```

Return the complete pipeline definition, including its ordered steps.

### Update pipeline

```text
PATCH /api/v1/pipelines/{pipeline_id}
```

Use partial updates.

After applying the patch, validate the complete resulting pipeline.

Replacing `steps` replaces the complete ordered steps array. Do not implement individual step mutation endpoints yet.

Support updating:

* `title`
* `description`
* `enabled`
* `steps`

### Delete pipeline

```text
DELETE /api/v1/pipelines/{pipeline_id}
```

Archive the pipeline instead of physically deleting it.

Archived pipelines:

* Must not appear in standard listings.
* Cannot be edited.
* Cannot be enabled.
* Will not be executable when pipeline execution is implemented.

Follow the existing deletion response conventions.

## Changelog

Reuse the existing changelog implementation.

Create changelog entries for:

* Pipeline creation.
* Title changes.
* Description changes.
* Step changes.
* Enable or disable changes.
* Archival.

For step updates, store a useful diff showing:

* Added steps.
* Removed steps.
* Changed steps.
* Order changes.

Because steps have no stable unique ID, compare them by array position and serialized content.

Do not create a separate event or audit system.

## Error codes

Add stable application error codes consistent with the existing error envelope:

```text
pipeline_not_found
pipeline_archived
invalid_pipeline_steps
unsupported_pipeline_step
unsupported_human_gate_type
loop_not_found
```

Use:

* `404` when the pipeline or referenced loop does not exist.
* `409` when attempting to modify an archived pipeline.
* `422` for invalid pipeline definitions.

## Architecture

Follow the existing MVC project structure.

Keep responsibilities separated:

* Models define persisted entities.
* Schemas validate API input and output.
* Services contain pipeline validation and business rules.
* Repositories handle persistence.
* Controllers expose HTTP behaviour.

Reuse existing abstractions only where they already fit.

Do not introduce a generic workflow engine, state machine framework, or pipeline execution abstraction.

## Out of scope

Do not implement:

* Pipeline runs.
* Pipeline execution.
* Step execution.
* Human gate resolution.
* Approval submissions.
* Quiz generation.
* Quiz submission or scoring.
* Quiz attempts.
* Model selection for quizzes.
* Conditional steps.
* Parallel branches.
* Input or output mappings.
* Individual step CRUD endpoints.
* Pipeline versioning.
* Frontend changes.
* Notifications.
* Queue infrastructure.

## Tests

Add unit and integration tests covering:

* Creation with two valid steps.
* Rejection with zero steps.
* Rejection with one step.
* Multiple references to the same loop.
* Multiple identical human gate steps.
* Missing loop references.
* Unsupported step types.
* Unsupported human gate types.
* Approval human gates.
* Quiz human gates.
* Rejection of quiz content included in the pipeline definition.
* Preservation of step order.
* Complete replacement of steps through `PATCH`.
* Validation of the resulting pipeline after a partial update.
* Enabling and disabling.
* Archival.
* Exclusion of archived pipelines from listings.
* Changelog creation.
* Changelog step diffs.

Follow the repository coding rules:

* MVC architecture.
* REST conventions.
* FastAPI.
* Files below 300 lines.
* Module docstrings.
* Documentation for public classes and functions.
* Brief comments explaining non-obvious decisions.
* Tests for every new behaviour.
* No unrelated refactoring.
* No functionality beyond what is explicitly requested.

Run:

```bash
pytest -q
```

Fix all failures before finishing.

Commit the implementation in small, focused commits directly to the current branch.

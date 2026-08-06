# Pipelines

A pipeline stores an ordered sequence of loop references and human checkpoints.
The API manages and validates the definition but does not execute it.

## Pipeline calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/pipelines` | Lists ten filtered pipelines after an offset. |
| `POST` | `/api/v1/pipelines` | Creates an enabled pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}` | Returns one complete ordered definition. |
| `PATCH` | `/api/v1/pipelines/{pipeline_id}` | Updates mutable fields or enablement. |
| `DELETE` | `/api/v1/pipelines/{pipeline_id}` | Archives the pipeline. |
| `GET` | `/api/v1/pipelines/{pipeline_id}/changelog` | Lists ten newest changelog entries. |

Creation requires a non-empty `title`, a `description`, and at least two steps.
New pipelines are enabled. PATCH accepts `title`, `description`, `enabled`, and
`steps`; supplying `steps` replaces the complete ordered array. Archived
pipelines are immutable and omitted from unfiltered listings.

The list accepts a non-negative `offset`, optional case-insensitive `search`
over title and description, and optional `status` of `active`, `disabled`, or
`archived`. Active pipelines sort before disabled and archived pipelines.

## Pipeline steps

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

Quiz gates require `config` and `minimum_correct_answers`. `question_count`
defaults to `10` and `option_count` defaults to `3`:

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
discriminator failures use `unsupported_pipeline_step`, human-gate discriminator
failures use `unsupported_human_gate_type`, and other invalid step structures
use `invalid_pipeline_steps`.

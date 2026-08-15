# Loops and Roles

This document defines the role model for persisted loops and distinguishes it
from the loop-run behavior implemented today.

## Role model

A loop agent stores a model, persona, and one role:

- `generator`: produces a candidate solution or proposed output;
- `reviewer`: evaluates a candidate and supplies feedback for a later revision;
- `aggregator`: synthesizes multiple candidate outputs into one consolidated
  result.

The role vocabulary is defined in `src/app/models/loop.py` and exposed by
`src/app/schemas/loop.py`. Loop agents do not have separate domain classes by
role.

## Flow validation

`src/app/services/loops/validation.py` validates agent role cardinality for
three loop flows:

| Type of loop | Number of generators | Number of reviewers | Number of aggregators |
| --- | --- | --- | --- |
| Direct | Exactly 1 | 0 | 0 |
| Refinement | Exactly 1 | At least 1 | 0 |
| Roundtable | At least 2 | 0 | Exactly 1 |

These rules define valid loop resources. They also apply to loop-backed
activities, including inline Pipeline activities.

## Implemented loop-run behavior

The loop-run executor in `src/app/services/loop_runs/service.py` supports
`direct` and `roundtable` loops.

A direct loop executes its generator and turns its JSON response into file
operations. A roundtable executes every generator and sends their proposals to
its aggregator. The aggregator returns the final JSON file-operation plan.

Only the final operation plan reaches the CLI `apply_operations` and
`commit_if_allowed` checkpoints. The executor still rejects `refinement` flow.

## Instruction library support

`src/app/services/execution_instructions/library.py` recognizes `generator` and
`reviewer` as default executable instruction roles. Builtin persona metadata
also declares applicability for those roles.

The loop-run executor resolves each configured agent persona from the SQL
instruction library and prefixes its model prompt with that content. This
includes the aggregator's `editor` persona, even though `aggregator` is not a
default instruction-library role.

## Selected roundtable sequence

Roundtable execution follows this sequence:

1. Each generator produces a proposal.
2. The aggregator synthesizes the proposals into one final result.

Only the aggregator's final operation plan reaches the CLI `apply_operations`
and `commit_if_allowed` checkpoints. The CLI does not apply individual generator
proposals.

Refinement loops are structurally validated but cannot currently create runs.

## Related files

- `src/app/models/loop.py`;
- `src/app/schemas/loop.py`;
- `src/app/services/loops/validation.py`;
- `src/app/services/loop_runs/service.py`;
- `src/app/services/execution_instructions/library.py`.

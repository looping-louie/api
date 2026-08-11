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

- `direct`: at least one agent and at most one aggregator;
- `refinement`: exactly one generator, at least one reviewer, and at most one
  aggregator;
- `roundtable`: at least two generators and exactly one aggregator. Reviewers
  are optional.

These rules define valid loop resources. They do not by themselves execute
agents.

## Catalog examples

The builtin loops in `src/app/catalogs/loops/catalog.py` use the `roundtable`
flow:

- `shape ideas` assigns `product_manager` and `ux_designer` as generators,
  `devils_advocate` as a reviewer, and `editor` as an aggregator;
- `plan implementation` assigns `tech_lead` and `platform_architect` as
  generators, `devils_advocate` as a reviewer, and `editor` as an aggregator.

The output contracts specify the final expected document or JSON. They do not
specify the sequencing of generator, reviewer, and aggregator calls.

## Implemented loop-run behavior

The loop-run executor in `src/app/services/loop_runs/service.py` supports
`direct` and `roundtable` loops.

A direct loop executes one generator and turns its JSON response into file
operations. A roundtable executes every generator, sends the proposals to every
reviewer, and sends the proposals and critique to one aggregator. The
aggregator returns the final JSON file-operation plan.

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
2. Each reviewer evaluates the generator proposals and provides critique.
3. The aggregator synthesizes the proposals and critique into one final result.

Only the aggregator's final operation plan reaches the CLI `apply_operations`
and `commit_if_allowed` checkpoints. The CLI does not apply individual generator
proposals.

Roundtable does not yet use `max_iterations` for reviewer-triggered retries.
Iteration-based refinement remains a later enhancement.

## Alternative roundtable modeling

The selected sequence is not the only valid roundtable design. These
alternatives remain available if product requirements change:

- **Post-aggregation review gate:** the aggregator first synthesizes generator
  proposals. Reviewers then evaluate the consolidated result. A rejection starts
  another generator and aggregation iteration, bounded by `max_iterations`.
- **Advisory reviewers:** reviewers produce critique artefacts for users or later
  workflows, but their feedback neither changes the aggregator prompt nor blocks
  the final aggregated result.

The post-aggregation model treats reviewer output as a revision gate. The
advisory model treats it as non-blocking information. Neither model is
implemented in the current loop-run executor.

## Related files

- `src/app/models/loop.py`;
- `src/app/schemas/loop.py`;
- `src/app/services/loops/validation.py`;
- `src/app/services/loop_runs/service.py`;
- `src/app/services/execution_instructions/library.py`;
- `src/app/catalogs/loops/catalog.py`.

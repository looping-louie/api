---
id: task_decomposition
name: Task Decomposition
category: implementation_planning
description: >
  Provides methods for converting an approved idea or specification into
  small, ordered, independently reviewable implementation tasks with clear
  boundaries, dependencies, context, and commit outcomes.
phase: deliberation
artifacts:
    - prompt
    - current_artifact
    - contributions
output: json
---

# Task Decomposition

## Scope

This skill covers the conversion of an approved idea, specification, or desired
outcome into an ordered implementation backlog.

It applies when producing tasks that will be executed sequentially by developers
or automated coding harnesses.

A good task must be:

- understandable without the meeting transcript;
- small enough for one focused implementation run;
- independently reviewable;
- ordered by dependency;
- explicit about acceptance criteria;
- bounded by the approved scope and non-goals;
- suitable for one coherent commit.

## Decomposition principles

### Decompose by observable outcome

Prefer vertical slices that produce a verifiable result.

A vertical slice may include the minimum required:

- data model;
- backend behaviour;
- user interface;
- validation;
- tests;
- configuration.

Avoid decomposing solely by technical layer when no layer produces a usable or
reviewable outcome.

Good:

- create the empty ideas page and navigation entry;
- add creation form validation and local submission behaviour;
- persist created ideas and load them in the list.

Weak:

- write HTML;
- write CSS;
- write JavaScript.

Layer-based tasks are acceptable when architecture, migration, or repository
constraints require them.

### Preserve dependency order

Order tasks so each task depends only on:

- existing repository state;
- completed earlier tasks;
- explicitly available external systems.

Typical ordering may be:

1. establish shared contracts or schema;
2. build the smallest end-to-end path;
3. add secondary states and validation;
4. add integrations;
5. add migration or rollout controls;
6. add targeted hardening and tests.

Do not place a consumer before the contract or capability it requires.

### Keep tasks small and coherent

One task should have one primary reason to change.

Split a task when it contains several independently valuable or risky outcomes.

Combine work when splitting it would create:

- invalid intermediate states;
- unused abstractions;
- temporary duplication;
- impossible review;
- artificial commits with no meaningful result.

A task is too large when:

- its prompt contains several unrelated verbs;
- it spans many independent flows;
- success cannot be verified with one concise set of criteria;
- failure would require discarding substantial unrelated work;
- reviewers need different contexts for different parts.

### Preserve approved scope

Every task should map to:

- a scope item;
- a validation need;
- a required risk treatment;
- an enabling dependency.

Do not create tasks for speculative future features.

Non-goals must remain excluded unless a task explicitly revises the approved
idea.

### Include necessary context

Each task prompt should state:

- the objective;
- relevant current repository or product context;
- files, routes, contracts, or systems involved when known;
- expected behaviour;
- important constraints;
- acceptance criteria;
- explicit exclusions;
- dependency assumptions.

Do not require the executor to infer critical decisions from task titles.

### Make acceptance observable

Acceptance criteria should describe what can be inspected or tested.

Use criteria such as:

- route renders the intended state;
- API rejects invalid input with a defined status;
- data is persisted with the expected fields;
- keyboard interaction works;
- direct navigation succeeds;
- tests cover the changed contract;
- no external integration is introduced yet.

Avoid:

- make it clean;
- improve UX;
- ensure quality;
- implement properly.

### One coherent commit

The commit message should describe the completed outcome.

Prefer imperative messages such as:

- Add ideas empty state
- Persist council selections
- Validate idea creation form
- Add task planning endpoint

Avoid vague messages such as:

- Update files
- Changes
- WIP
- Fix stuff

## Task categories

### Enabling tasks

Use only when a later outcome genuinely requires:

- schema or contract changes;
- shared infrastructure;
- migration preparation;
- test fixtures;
- provider configuration.

Avoid generic platform work that is not required by the approved idea.

### Product-flow tasks

These implement user-visible or externally observable behaviour.

Include:

- primary flow;
- empty, loading, success, and failure states where relevant;
- navigation;
- validation;
- permissions;
- persistence;
- external effects.

### Discovery tasks

Use a discovery or spike task when implementation depends on unresolved
feasibility.

A discovery task must produce:

- a decision;
- evidence;
- constraints;
- a recommendation;
- no unnecessary production abstraction.

Do not disguise undefined implementation work as a spike.

### Migration and rollout tasks

Where relevant, separate:

- backward-compatible preparation;
- data migration;
- application cutover;
- cleanup;
- rollback verification.

Do not combine an irreversible migration with unrelated feature work.

### Hardening tasks

Add separate hardening only when it is not part of the minimum safe
implementation.

Examples:

- performance work based on evidence;
- advanced observability;
- expanded browser support;
- load testing;
- security review remediation.

Fundamental correctness, authorisation, data integrity, and accessibility of the
primary flow belong in the original task, not a later hardening task.

## Dependency checks

For each task, identify whether it depends on:

- another task;
- external credentials;
- provider configuration;
- data migration;
- design decisions;
- legal approval;
- infrastructure;
- unavailable content;
- customer validation.

If a dependency is unresolved, either:

- create an earlier task that resolves it;
- preserve it as a blocker;
- remove the dependent task from the executable backlog.

## Automated harness suitability

For tasks executed by an LLM harness, check that:

- the task fits within repository context limits;
- the expected files or areas are identifiable;
- the task does not require hidden credentials;
- the task can be verified statically or by available tests;
- the task avoids broad unspecified refactors;
- the desired final state is explicit;
- the executor can complete it without asking product questions;
- the commit message matches one result.

Avoid tasks such as:

- improve the architecture;
- finish the frontend;
- add all necessary tests;
- make it production-ready.

## Common failure patterns

### Tasks mirror document headings

Correction:

- group work by implementation outcome and dependency, not by idea sections.

### Tasks are too broad

Correction:

- split independent flows, integrations, and risks.

### Tasks are too small

Correction:

- combine changes that only make sense together and should be reviewed as one
  result.

### Missing acceptance criteria

Correction:

- add observable behaviour, constraints, and failure states.

### Hidden dependencies

Correction:

- sequence enabling work or state the blocker explicitly.

### Scope creep during planning

Correction:

- map every task to approved scope, validation, or required risk treatment.

### Repeated context omitted

Correction:

- make each prompt self-contained even when tasks run sequentially.

## Output qualities

A strong implementation backlog is:

- ordered;
- bounded;
- self-contained;
- executable;
- reviewable;
- traceable to the approved idea;
- explicit about dependencies;
- suitable for small commits.

It should allow the implementation harness to process tasks sequentially without
inventing missing product decisions.

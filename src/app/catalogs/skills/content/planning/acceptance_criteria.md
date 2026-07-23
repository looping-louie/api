# Acceptance Criteria

## Scope

This skill covers the definition and review of acceptance criteria for product
ideas, implementation tasks, APIs, workflows, user interfaces, integrations,
and operational changes.

Acceptance criteria define the conditions under which a result is considered
complete and correct.

They should communicate observable behaviour without prescribing unnecessary
implementation detail.

## Core principles

### Describe outcomes, not activity

Acceptance criteria should state what becomes true.

Prefer:

- unauthenticated requests receive a 401 response;
- the empty state links to `/app/ideas/new`;
- every generated task has status `pending`;
- an idea document contains all required headings and no more than 1,000 words.

Avoid:

- write authentication code;
- create a component;
- use a loop;
- add CSS.

Implementation instructions may appear elsewhere in the task when architecture
requires them.

### Make criteria observable

A criterion should be verifiable through:

- user interaction;
- rendered output;
- API response;
- stored state;
- emitted event;
- generated file;
- log or metric;
- automated test;
- configuration inspection.

Avoid criteria based only on subjective judgement.

Replace "looks professional" with concrete constraints such as:

- uses the existing app shell;
- preserves the current spacing and typography tokens;
- includes visible hover and focus states;
- supports the defined mobile breakpoint.

### Cover the relevant states

For changed behaviour, consider:

- initial;
- empty;
- loading;
- success;
- validation failure;
- permission failure;
- dependency failure;
- not found;
- conflict;
- retry;
- cancellation;
- disabled;
- direct navigation;
- repeated execution.

Do not require every state for every task. Include states that are relevant to
the changed contract.

### Define boundaries

Acceptance criteria should make important limits explicit.

Examples:

- maximum length;
- allowed status values;
- required keys;
- supported file types;
- permission scope;
- timeout;
- route pattern;
- number of items;
- locale or browser support;
- excluded integrations.

Boundaries reduce interpretation drift.

### Preserve scope and non-goals

Criteria should verify the approved scope.

They should not introduce new product requirements during implementation.

Where an omission could be mistaken for incomplete work, state it explicitly:

- data remains local in this task;
- no Supabase connection is introduced;
- authentication is outside the task;
- only the empty state is implemented;
- existing public URLs remain unchanged.

### Separate acceptance from quality aspirations

Acceptance criteria should include quality requirements when they are necessary
for correctness or the user outcome.

Examples:

- the primary flow is keyboard operable;
- protected data is authorised server-side;
- repeated webhook delivery does not duplicate the effect;
- the page returns a real 404 for missing content.

Avoid turning broad aspirations into untestable blockers:

- use best practices;
- be scalable;
- follow clean code;
- make it secure.

Translate material aspirations into concrete behaviour or constraints.

## Criterion structure

A criterion may use:

- declarative statements;
- Given/When/Then;
- input/output examples;
- invariants;
- schema examples;
- state tables.

Choose the simplest form that removes ambiguity.

### Declarative criteria

Useful for straightforward contracts:

- The response is a JSON array.
- Every item contains exactly five required keys.
- Task IDs are unique.
- `run_id` is an empty string.

### Given/When/Then

Useful for stateful or interactive behaviour:

- Given no ideas exist, when the user opens `/app/ideas`, then the page displays
  the empty state and a primary action to create the first idea.

Avoid verbose scenarios for simple static requirements.

### Invariants

Useful for system properties:

- A user can never access another tenant's idea.
- Retrying the same request with the same idempotency key does not duplicate the
  operation.
- A completed task never returns to `pending`.

### Examples

Examples clarify formats but should not accidentally become the only accepted
case unless that restriction is intended.

## Review checks

Check that each criterion is:

- relevant to the task;
- observable;
- unambiguous;
- internally consistent;
- feasible within the stated appetite;
- independent from optional future work;
- compatible with project conventions;
- clear about error or edge behaviour where material;
- testable with available evidence or tooling.

Check the complete set for:

- contradictions;
- duplicated requirements;
- missing primary-flow behaviour;
- hidden implementation decisions;
- scope expansion;
- undefined terms;
- assumptions presented as facts.

## API acceptance criteria

Where applicable, define:

- method and route;
- authentication requirement;
- request schema;
- validation behaviour;
- response schema;
- success status;
- error statuses;
- authorisation;
- idempotency;
- side effects;
- pagination or limits;
- compatibility expectations.

Do not accept TypeScript types as runtime validation criteria.

## UI acceptance criteria

Where applicable, define:

- route or entry point;
- rendered states;
- primary actions;
- navigation outcome;
- validation feedback;
- keyboard behaviour;
- accessible names and labels;
- responsive constraints;
- loading and failure behaviour;
- data source or temporary mock boundary.

Avoid prescribing exact DOM structure unless semantics are part of the
requirement.

## Data acceptance criteria

Where applicable, define:

- required fields;
- types;
- uniqueness;
- nullability;
- defaults;
- relationships;
- migration behaviour;
- deletion or retention;
- tenant boundaries;
- serialised representation.

### Generated artifact criteria

For Markdown or JSON output, define:

- required structure;
- ordering;
- maximum length;
- exact keys;
- allowed values;
- uniqueness;
- whether additional fields are permitted;
- whether commentary or code fences are forbidden.

## Common failure patterns

### Subjective completion

Correction:

- replace adjectives with observable behaviour or constraints.

### Criteria restate the task title

Correction:

- describe the states and outputs that demonstrate completion.

### Missing failure states

Correction:

- include material validation, permission, dependency, or conflict behaviour.

### Over-specification

Correction:

- remove internal implementation choices that do not affect the contract.

### Hidden scope growth

Correction:

- compare each criterion with approved scope and non-goals.

### Untestable absolutes

Correction:

- define the evidence, environment, range, or threshold.

### Contradictory criteria

Correction:

- resolve precedence before implementation begins.

## Output qualities

Strong acceptance criteria are:

- concise;
- observable;
- testable;
- complete for the requested scope;
- free of implementation trivia;
- explicit about meaningful boundaries;
- suitable for both implementation and review.

They should enable an executor and a reviewer to reach the same conclusion about
whether the work is complete.

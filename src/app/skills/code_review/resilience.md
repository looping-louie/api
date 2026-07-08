---
id: resilience
name: Resilience
category: reliability_review
description: >
  Provides cross-cutting resilience knowledge for failure handling, retries,
  idempotency, degradation, recovery, observability, rollback, dependency
  failure, state integrity, and operational continuity.
phase: review
artifacts:
    - prompt
    - current_artifact
    - changed_files
output: json
---

# Resilience

## Scope

This skill covers the ability of a product, service, workflow, or implementation
to continue operating safely when components fail, inputs are invalid,
dependencies are unavailable, or execution is interrupted.

It applies to:

- web applications;
- APIs;
- background jobs;
- queues;
- integrations;
- data pipelines;
- deployment workflows;
- multi-step user actions;
- distributed systems;
- human-operated processes.

Resilience is not the absence of failure. It is the ability to limit impact,
preserve correctness, recover predictably, and communicate the current state.

## Failure model

### Identify failure modes

Check for failures caused by:

- invalid input;
- partial data;
- timeouts;
- unavailable dependencies;
- rate limits;
- duplicate requests;
- stale responses;
- interrupted execution;
- process restart;
- deployment change;
- network partition;
- storage exhaustion;
- concurrency;
- permission changes;
- corrupt state;
- incompatible versions;
- operator error.

Avoid designing only for the successful path.

### Define failure boundaries

Determine:

- which component detects the failure;
- which component owns recovery;
- which state changes have already occurred;
- whether work can be retried;
- whether the operation is reversible;
- what the user or operator should see;
- what evidence is needed for diagnosis.

Failures should be contained as close as practical to their source.

## State integrity

### Atomicity and partial completion

For multi-step operations, check whether partial completion can produce:

- inconsistent records;
- duplicate external effects;
- orphaned resources;
- incorrect status;
- lost updates;
- unauthorised access;
- misleading success.

Use transactions when all affected state belongs to one transactional boundary.

When a transaction cannot span dependencies, use explicit states, compensation,
or reconciliation.

### Idempotency

Operations that may be repeated should produce the same intended outcome.

Check:

- retryable mutations;
- webhook processing;
- payment or billing actions;
- task execution;
- message consumption;
- deployment hooks;
- external API writes.

Use stable idempotency keys or durable deduplication where duplicate effects
would be harmful.

Do not assume a client, queue, or provider delivers exactly once.

### Concurrency

Check for:

- races between reads and writes;
- conflicting updates;
- duplicated workers;
- stale optimistic state;
- lost updates;
- out-of-order events;
- overlapping retries.

Use version checks, uniqueness constraints, locks, leases, compare-and-set, or
other suitable coordination mechanisms.

## Dependency resilience

### Timeouts

Every remote call should have a deliberate timeout.

Timeouts should reflect:

- user expectations;
- dependency behaviour;
- remaining request budget;
- retry strategy;
- operational cost.

An unlimited wait is not a resilience strategy.

### Retries

Retry only when:

- the failure is likely transient;
- the operation is safe to repeat;
- the total retry budget is bounded;
- backoff and jitter reduce coordinated load;
- the final failure remains visible.

Avoid retries for:

- validation errors;
- authorisation failures;
- deterministic conflicts;
- destructive non-idempotent operations;
- requests already exceeding their deadline.

### Circuit breaking and load shedding

Where dependency failure can cascade, consider:

- circuit breakers;
- concurrency limits;
- queue bounds;
- admission control;
- fallback responses;
- reduced functionality;
- graceful rejection.

Protect the system from doing unlimited work under failure.

### Fallbacks

A fallback should preserve correctness.

Possible fallbacks include:

- cached public data;
- read-only mode;
- delayed processing;
- manual review;
- simplified output;
- unavailable-state messaging.

Do not serve stale, private, or incorrect data merely to avoid an error.

## User and operator experience

### Error states

Check that failures:

- use the correct status or state;
- explain what happened without leaking internals;
- distinguish validation, permission, conflict, rate-limit, dependency, and
  internal failures;
- provide a useful next step;
- do not claim success prematurely;
- preserve user-entered data where practical.

### Progress and uncertainty

Long-running operations should expose:

- accepted;
- queued;
- running;
- completed;
- failed;
- cancelled;
- partially completed.

Avoid indefinite spinners without an observable state.

### Recovery actions

Users and operators should know whether to:

- retry;
- wait;
- correct input;
- contact support;
- resume;
- roll back;
- reconcile.

Recovery actions must be safe and effective.

## Operational resilience

### Observability

Material operations should produce enough evidence to determine:

- what failed;
- when;
- for whom or which tenant;
- at which stage;
- with which dependency;
- whether retries occurred;
- whether state changed;
- whether recovery succeeded.

Use structured logs, metrics, traces, and domain events without exposing secrets
or unnecessary personal data.

### Health and readiness

Distinguish:

- process health;
- readiness to receive traffic;
- dependency health;
- degraded operation.

Do not report healthy merely because the process is running.

### Rollback and forward recovery

Check that changes have an intentional recovery path.

Consider:

- backward-compatible database changes;
- feature flags;
- reversible configuration;
- version compatibility;
- deployment rollback;
- data repair;
- replay or reconciliation;
- forward fixes when rollback is unsafe.

A rollback that cannot reverse data changes is incomplete.

### Capacity and overload

Check for:

- unbounded queues;
- unbounded memory growth;
- uncontrolled fan-out;
- excessive concurrency;
- missing rate limits;
- storage growth;
- expensive pathological input.

The system should fail predictably before exhausting shared resources.

## Planning checks

For ideas and implementation plans, check that:

- failure states are included where they affect the main flow;
- retry and idempotency needs are visible;
- critical dependencies are identified;
- recovery and rollback are not deferred implicitly;
- operational ownership exists;
- tasks include observability where necessary;
- data migrations preserve compatibility;
- risky changes are sequenced to allow recovery.

## Common failure patterns

### Happy-path-only implementation

Correction:

- identify dependency, validation, concurrency, and interruption failures.

### Blind retry

Correction:

- classify errors;
- require idempotency;
- bound attempts and duration.

### Error converted into empty success

Correction:

- preserve failure semantics;
- show an intentional unavailable or error state.

### Process-local reliability assumptions

Correction:

- account for restart, horizontal scaling, and duplicate execution.

### Missing rollback

Correction:

- define how code, configuration, and data return to a safe state.

### Observability without action

Correction:

- connect alerts and states to an owner and recovery procedure.

## Output qualities

A resilient design or implementation is:

- explicit about failure;
- bounded under overload;
- safe to retry where necessary;
- protective of state integrity;
- observable;
- recoverable;
- clear to users and operators;
- compatible with the intended deployment model.

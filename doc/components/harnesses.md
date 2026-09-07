# Harnesses

A Harness is the local execution mechanism for a runtime-executable Activity.
It is distinct from an Activity agent: an agent is a generator, reviewer, or
aggregator role backed by a Persona and model selection; a Harness carries out
the Activity in a worker's configured checkout and reports normalized results.

## Ownership

The API owns Harness selection, immutable execution snapshots, loop semantics,
checkpoint validation, durable execution state, and commit authorization. The
runtime owns local repository execution, checkout paths, executable locations,
credentials, and other machine configuration.

The API-directed repository executor is the `louie` Harness. It collects
repository context, applies API-approved file operations, gathers review input,
and commits only when the API authorizes the handoff. `louie` v1 is the
compatibility default for existing Pipelines.

Human Activities (`approval` and `quiz`) do not use a selected Harness. They
use the built-in `human` execution mode and accept only human decision
checkpoints.

## Selection

PipelineRun creation resolves a Harness from Activity, Pipeline, then User
scope. It freezes the effective Harness independently for every
runtime-executable Activity run. When no candidate exists, the API freezes the
`louie` v1 compatibility default. A Pipeline edit does not change the Harness
used by an existing run.

A Harness has a stable `kind`, a `version`, and a kind-specific `config`
object. The API accepts `louie` v1, `codex_cli` v1, and `copilot_cli` v1 with
an empty `config`.

```json
{
  "harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  }
}
```

## Worker Capability And Admission

Workers advertise their current Harness capabilities during registration and
may replace them on every heartbeat. A PipelineRun claim requires an active
Worker heartbeat and an exact match for the next claimable Activity's frozen
Harness selection.

A valid run remains queued when no compatible worker is healthy. It becomes
claimable without a user retry after a later heartbeat advertises the required
Harness. The run-readiness endpoint exposes Project-scoped aggregate counts and
the required Harness for operator diagnostics without exposing Worker identities
or local configuration. Registration and heartbeat requests carry both the
acting `X-User-ID` and selected `X-Project-ID`.

## CLI Harness Execution

`codex_cli` and `copilot_cli` support `direct_loop`, `refinement_loop`, and
`roundtable_loop`.
The API owns their shared semantics and persists one `run_harness` checkpoint
per agent turn: writer execution, read-only proposal, read-only review, or
writer aggregation. This lets another Harness adapter implement the same roles
without duplicating loop state or commit policy.

For each CLI Harness Activity, PipelineRun creation freezes every agent's
effective model as `requested_model`, resolves each selected Persona and its
ordered Skills from the User-owned instruction library, and freezes their IDs,
versions, metadata, and content in the Activity snapshot. The runtime receives
that model and instruction snapshot with the pending agent turn; neither the API
nor the runtime resolves mutable instruction resources during execution.

Neither CLI Harness selects API Linked Services or requires API provider
credentials. A CLI Harness Activity without an effective model ID, with an
unknown or deprecated model, or with a model disabled by User policy fails
before the PipelineRun is persisted. CLI authentication remains local to the
worker.

## Result Envelope And Commit Handoff

The runtime reports a normalized, versioned observation through `run_harness`.
Every observation carries `schema_version` and the frozen Harness identity,
followed by timing, model, usage, process, Git, response, and error fields.
Harness-specific fields extend that common envelope. `codex_cli` v1 and
`copilot_cli` v1 include session reference and materialized Skill IDs and
versions; Codex additionally reports reasoning effort when available.

The API validates that the reported Harness and requested model match the
immutable Activity snapshot. It retains observations on both success and
failure, including partial observations from a failed process. PipelineRun
events record `harness_turn_completed` or `harness_turn_failed`; consumers
identify the concrete implementation through `payload.harness.kind`.

For commit-enabled CLI Harness runs, a successful result includes a proposed
`commit_message`. The API validates and persists the message as a runtime
artifact, then returns it only through the later `commit_if_allowed` checkpoint.
The CLI does not authorize or perform the commit. A successful authorized commit
updates the final commit SHA without discarding the Harness observation.

## Related Documentation

- [Execution](execution.md) describes the Activity-run checkpoint lifecycle.
- [Pipelines endpoint reference](../endpoints/pipelines.md) documents run
  creation, readiness, claims, and events.
- [Workers endpoint reference](../endpoints/workers.md) documents capability
  registration and heartbeats.

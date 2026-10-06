# Workers

Workers are API-provisioned runtime identities. New global Workers register
once, advertise capabilities once, and are explicitly enabled for each Project
where they may claim work. The runtime retains local checkout paths; the API
stores only Worker identities and Project execution authorization.

Legacy Workers remain Project-scoped during the migration. A runtime stores its
assigned `worker_id` in the Project configuration and refreshes a heartbeat
before each Project poll. An active heartbeat and a matching Harness capability
are required to claim a PipelineRun.

Worker provisioning is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/workers/instances` | Register a global Worker and enable its initial Project. |
| `POST` | `/api/v1/workers/instances/{worker_id}/projects/{project_id}` | Enable a global Worker for an additional Project. |
| `POST` | `/api/v1/workers` | Provision a worker identity. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh an existing worker heartbeat. |

Legacy endpoints require `X-User-ID` and use `X-Project-ID` to select one of
that User's Projects.

Global Worker endpoints require `X-User-ID`. Registration names its initial
Project in the request body, while a Project-enablement route names the Project
in its path. The requesting User must have access to each named Project.

## Register A Global Worker

`POST /api/v1/workers/instances` registers one global Worker and enables it for
the required `project_id`. Its `harnesses` array declares local execution
capabilities. The API does not receive checkout paths.

```http
POST /api/v1/workers/instances
X-User-ID: user-acme
Content-Type: application/json
```

```json
{
  "project_id": "project-acme",
  "harnesses": [
    {
      "kind": "codex_cli",
      "version": "v1",
      "config": {}
    }
  ]
}
```

Enable an additional Project only when the requesting User can access it:

```http
POST /api/v1/workers/instances/worker-local-01/projects/project-b
X-User-ID: user-acme
```

## Observe Worker Liveness

The API intentionally exposes no raw Worker list or identity read endpoint.
Runtimes verify their own registration by sending a heartbeat and inspecting
the returned `last_heartbeat_at`. Web clients diagnose queued work through
`GET /api/v1/pipelines/{pipeline_id}/runs/{run_id}/readiness`, which returns
only Project-scoped aggregate liveness and Harness-compatibility counts.
Pipeline-run claim admission remains the authoritative mutation-time check.

## Provision A Worker

`POST /api/v1/workers` provisions a worker identity in the selected Project.
Its required `harnesses` array declares local execution capabilities. Each
entry must explicitly name its `kind`; the API never infers `louie` or any
other Harness. Store the returned ID in that Project's runtime configuration.

An empty array registers a connected worker with no execution capabilities. It
remains visible to readiness checks but cannot claim a PipelineRun until a
heartbeat reports a Harness matching that run's frozen Harness.

```http
POST /api/v1/workers
X-User-ID: user-acme
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "harnesses": [
    {
      "kind": "louie",
      "version": "v1",
      "config": {
      }
    }
  ]
}
```

Example response (`201 Created`):

```json
{
  "id": "c1fa5f23a0fb4c4cad6b08a2ea774b21",
  "registered_at": "2026-08-21T10:00:00Z",
  "last_heartbeat_at": "2026-08-21T10:00:00Z",
  "harnesses": [
    {
      "kind": "louie",
      "version": "v1",
      "config": {
      }
    }
  ]
}
```

## Send A Heartbeat

`POST /api/v1/workers/{worker_id}/heartbeat` refreshes the liveness timestamp
for an existing provisioned worker. Its required `harnesses` array atomically
replaces the worker's currently observed capabilities, including replacing them
with an empty array. Workers report Harness health, not a model list:
`codex_cli` means that the configured executable and local login check currently
succeed. An unknown worker returns `404 worker_not_found`.

```http
POST /api/v1/workers/runtime-local-01/heartbeat
X-User-ID: user-acme
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "harnesses": [
    {
      "kind": "louie",
      "version": "v1",
      "config": {}
    },
    {
      "kind": "codex_cli",
      "version": "v1",
      "config": {}
    }
  ]
}
```

A queued PipelineRun is not invalid merely because no active worker currently
advertises its frozen Harness. It remains queued and can be claimed
automatically after a later heartbeat replaces the capability set with a
matching Harness.

# Workers

Workers are API-provisioned runtime identities. New global Workers register
once, advertise capabilities once, and are explicitly enabled for each Project
where they may claim work. The runtime retains local checkout paths; the API
stores only Worker identities and Project execution authorization.

Worker provisioning is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

A global Worker currently has capacity for one active, unexpired PipelineRun
lease across all of its enabled Projects. A claim made while that lease is
active returns `409 worker_capacity_unavailable`.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/workers?project_id={project_id}` | List global Workers enabled for one Project. |
| `GET` | `/api/v1/workers/{worker_id}` | Describe one global Worker enabled for the selected Project. |
| `POST` | `/api/v1/workers` | Register a global Worker and enable its initial Project. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh a global Worker heartbeat. |
| `POST` | `/api/v1/workers/{worker_id}/projects/{project_id}` | Enable a global Worker for an additional Project. |
Global Worker endpoints require `X-User-ID`. Registration names its initial
Project in the request body, while a Project-enablement route names the Project
in its path. The requesting User must have access to each named Project.

## Register A Global Worker

`POST /api/v1/workers` registers one global Worker and enables it for
the required `project_id`. Its `harnesses` array declares local execution
capabilities. The API does not receive checkout paths.

```http
POST /api/v1/workers
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
POST /api/v1/workers/worker-local-01/projects/project-b
X-User-ID: user-acme
```

## Heartbeat A Global Worker

`POST /api/v1/workers/{worker_id}/heartbeat` records one liveness
signal and atomically replaces the global Worker's observed Harness
capabilities. The caller must provide `X-User-ID` and select an accessible
Project with `X-Project-ID` when they belong to multiple Projects. The selected
Project authorizes the request; the heartbeat itself remains global to the
Worker.

```http
POST /api/v1/workers/worker-local-01/heartbeat
X-User-ID: user-acme
X-Project-ID: project-acme
Content-Type: application/json
```

```json
{
  "harnesses": [
    {
      "kind": "codex_cli",
      "version": "v1",
      "config": {}
    }
  ]
}
```

## List Global Workers

`GET /api/v1/workers?project_id={project_id}` returns global Workers enabled for
the requested Project. The caller must have access to that Project. It exposes
the Worker identity, last heartbeat, observed Harnesses, that Project's
enablement time, and server-calculated `active` state. `active_claims` counts
the Worker's active leases across all enabled Projects; `capacity` is currently
fixed at `1`. It does not expose the Worker's enablements in other Projects.

```http
GET /api/v1/workers?project_id=project-acme
X-User-ID: user-acme
```

```json
[
  {
    "id": "worker-local-01",
    "registered_at": "2026-10-07T10:00:00Z",
    "last_heartbeat_at": "2026-10-07T10:01:00Z",
    "harnesses": [
      { "kind": "codex_cli", "version": "v1", "config": {} }
    ],
    "enabled_at": "2026-10-07T10:00:00Z",
    "active": true,
    "active_claims": 0,
    "capacity": 1
  }
]
```

## Describe A Global Worker

`GET /api/v1/workers/{worker_id}` returns the same Project-scoped operational
state as the list item for one Worker. It returns `404 worker_not_found` when
the Worker is not enabled for the Project selected by `X-Project-ID`.

```http
GET /api/v1/workers/worker-local-01
X-User-ID: user-acme
X-Project-ID: project-acme
```

Pipeline-run readiness remains the aggregate diagnosis for one queued run, and
claim admission remains the authoritative mutation-time capability check.

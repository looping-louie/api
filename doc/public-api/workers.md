# Workers

Workers are API-provisioned, User-owned runtime identities. New Workers
register once, advertise capabilities once, and are explicitly enabled for each
Project where they may claim work. The runtime retains local checkout paths;
the API stores only Worker identities and Project execution authorization.

Worker provisioning is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

A Worker currently has capacity for one active, unexpired PipelineRun
lease across all of its enabled Projects. A claim made while that lease is
active returns `409 worker_capacity_unavailable`.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/workers` | List Workers owned by the requesting User. |
| `GET` | `/api/v1/workers/{worker_id}` | Describe one Worker owned by the requesting User. |
| `POST` | `/api/v1/workers` | Register a Worker and enable its initial Project. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh a Worker heartbeat. |

Worker endpoints require `X-User-ID`. Registration names its initial Project in
the request body. The requesting User must own the Worker and have access to
that Project.

## Register A Worker

`POST /api/v1/workers` registers one Worker and enables it for
the required `project_id`. Its `harnesses` array declares local execution
capabilities. The API does not receive checkout paths.

```http
POST /api/v1/workers
X-User-ID: user-acme
```

## Heartbeat A Worker

`POST /api/v1/workers/{worker_id}/heartbeat` records one liveness
signal and atomically replaces the Worker's observed Harness
capabilities. The caller must provide `X-User-ID` and own the Worker. A
heartbeat is global to the Worker and does not require `X-Project-ID`.

```http
POST /api/v1/workers/worker-local-01/heartbeat
X-User-ID: user-acme
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

## List Workers

`GET /api/v1/workers` returns Workers **owned** by the requesting User. It returns
Worker identity and observed Harness state only; Project enablement fields such
as `enabled_at` do not belong to this representation. To inspect Workers
enabled for a Project, use the [Project Worker collection](projects.md#list-project-workers).

```http
GET /api/v1/workers
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
    ]
  }
]
```

## Describe A Worker

`GET /api/v1/workers/{worker_id}` returns Worker identity and observed Harness
state. It does not require `X-Project-ID` and does not include Project
enablement fields such as `enabled_at`. It returns `404 worker_not_found` when
the Worker is not owned by the requesting User.

```http
GET /api/v1/workers/worker-local-01
X-User-ID: user-acme
```

Pipeline-run readiness remains the aggregate diagnosis for one queued run, and
claim admission remains the authoritative mutation-time capability check.

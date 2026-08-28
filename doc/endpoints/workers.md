# Workers

Workers are API-provisioned, Project-scoped runtime identities. A runtime
stores its assigned `worker_id` in the Project configuration and refreshes a
heartbeat before each Project poll. An active heartbeat and a matching
Harness capability are required to claim a PipelineRun.

Worker provisioning is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/workers` | Provision a worker identity. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh an existing worker heartbeat. |

Both endpoints use `X-Project-ID` to select the worker's Project.

## Observe Worker Liveness

The API intentionally exposes no `GET` worker list or read endpoint. To verify
that a configured worker identity remains available before queueing work, send
its heartbeat request and inspect the returned `last_heartbeat_at` timestamp.
The successful heartbeat confirms the worker identity belongs to the selected
Project and refreshes its liveness signal. Pipeline-run claim admission
remains the authoritative check that an active worker can claim queued work.

## Provision A Worker

`POST /api/v1/workers` provisions a worker identity in the selected Project.
Its optional `harnesses` array declares local execution capabilities. Omitting
the request body registers the compatibility default: `louie` v1 with an empty
configuration. Store the returned ID in that Project's runtime configuration.

```http
POST /api/v1/workers
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
for an existing provisioned worker. An unknown worker returns
`404 worker_not_found`.

```http
POST /api/v1/workers/runtime-local-01/heartbeat
X-Project-ID: project-acme
```

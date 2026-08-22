# Workers

Workers are API-provisioned, workspace-scoped runtime identities. A runtime
stores its assigned `worker_id` in the workspace configuration and refreshes a
heartbeat before each workspace poll. An active heartbeat is required to claim
a PipelineRun.

Worker provisioning is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `POST` | `/api/v1/workers` | Provision a worker identity. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh an existing worker heartbeat. |

Both endpoints use `X-Workspace-ID` to select the worker's workspace.

## Observe Worker Liveness

The API intentionally exposes no `GET` worker list or read endpoint. To verify
that a configured worker identity remains available before queueing work, send
its heartbeat request and inspect the returned `last_heartbeat_at` timestamp.
The successful heartbeat confirms the worker identity belongs to the selected
workspace and refreshes its liveness signal. Pipeline-run claim admission
remains the authoritative check that an active worker can claim queued work.

## Provision A Worker

`POST /api/v1/workers` provisions a worker identity in the selected workspace.
Store the returned ID in that workspace's runtime configuration.

```http
POST /api/v1/workers
X-Workspace-ID: workspace-acme
```

Example response (`201 Created`):

```json
{
  "id": "c1fa5f23a0fb4c4cad6b08a2ea774b21",
  "registered_at": "2026-08-21T10:00:00Z",
  "last_heartbeat_at": "2026-08-21T10:00:00Z"
}
```

## Send A Heartbeat

`POST /api/v1/workers/{worker_id}/heartbeat` refreshes the liveness timestamp
for an existing provisioned worker. An unknown worker returns
`404 worker_not_found`.

```http
POST /api/v1/workers/runtime-local-01/heartbeat
X-Workspace-ID: workspace-acme
```

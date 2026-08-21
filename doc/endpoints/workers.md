# Workers

Workers are workspace-scoped runtime identities. A configured runtime registers
its stable `worker_id` before polling and refreshes a heartbeat before each
workspace poll. An active heartbeat is required to claim a PipelineRun.

Worker registration is separate from a PipelineRun lease. A heartbeat does not
extend a lease, and an expired heartbeat does not revoke an existing lease.

## Resource Endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `PUT` | `/api/v1/workers/{worker_id}` | Create or refresh a worker registration. |
| `POST` | `/api/v1/workers/{worker_id}/heartbeat` | Refresh an existing worker heartbeat. |

Both endpoints use `X-Workspace-ID` to select the registered workspace.

## Register A Worker

`PUT /api/v1/workers/{worker_id}` creates a worker registration in the selected
workspace. Repeating the request refreshes the heartbeat while preserving the
original registration timestamp.

```http
PUT /api/v1/workers/runtime-local-01
X-Workspace-ID: workspace-acme
```

Example response (`201 Created`):

```json
{
  "id": "runtime-local-01",
  "registered_at": "2026-08-21T10:00:00Z",
  "last_heartbeat_at": "2026-08-21T10:00:00Z"
}
```

## Send A Heartbeat

`POST /api/v1/workers/{worker_id}/heartbeat` refreshes the liveness timestamp
for an existing registration. An unknown worker returns `404 worker_not_found`.

```http
POST /api/v1/workers/runtime-local-01/heartbeat
X-Workspace-ID: workspace-acme
```

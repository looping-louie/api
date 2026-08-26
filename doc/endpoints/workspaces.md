# Workspaces

Users own Workspaces. Creating a Workspace creates an `owner` membership for
the requesting User. The first Workspace owned by a User becomes its default;
later Workspaces require `X-Workspace-ID` when the User needs to select one.

Workspace defaults store optional model-target and Harness overrides for the
selected workspace. They are configuration candidates for the hierarchical
execution-default system. Pipeline, Activity, and loop-agent configuration can
define narrower persisted overrides. PipelineRun creation uses Workspace values
only when no narrower Pipeline, Activity, or agent candidate supplies that
execution dimension, then freezes the effective value in its run snapshots.

## Workspace calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/workspaces` | List Workspaces accessible to the current User. |
| `POST` | `/api/v1/workspaces` | Create a Workspace owned by the current User. |
| `GET` | `/api/v1/workspaces/defaults` | Describes workspace default overrides. |
| `PUT` | `/api/v1/workspaces/defaults` | Replaces all workspace default overrides. |

## List workspaces

`GET /api/v1/workspaces` returns every Workspace accessible to the User
identified by `X-User-ID`. The default Workspace appears first.

```http
GET /api/v1/workspaces
X-User-ID: user-123
```

Example response (`200 OK`):

```json
[
  {
    "id": "workspace-acme",
    "name": "Acme",
    "created_at": "2026-08-26T10:00:00Z",
    "updated_at": "2026-08-26T10:00:00Z"
  }
]
```

## Create workspace

`POST /api/v1/workspaces` creates a Workspace owned by the User identified by
`X-User-ID`. The User must first be registered through `POST /api/v1/users`.

```http
POST /api/v1/workspaces
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "Acme"
}
```

Example response (`201 Created`):

```json
{
  "id": "workspace-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

`model_target` selects one configured linked service and one logical catalog
model. The linked service must belong to the selected workspace, be enabled and
configured, and support an active deployment for `model_id`. `harness` selects
one supported local execution mechanism. Both fields are nullable; `null`
means inherit rather than choose a workspace override.

## Describe workspace defaults

`GET /api/v1/workspaces/defaults` returns the selected workspace's stored
overrides. A workspace with no configured record returns both values as `null`.

```http
GET /api/v1/workspaces/defaults
X-Workspace-ID: workspace-acme
```

Example response (`200 OK`):

```json
{
  "model_target": {
    "linked_service_id": "linked-service-openai-primary",
    "model_id": "gpt-5"
  },
  "harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  },
  "updated_at": "2026-08-25T10:00:00Z"
}
```

## Replace workspace defaults

`PUT /api/v1/workspaces/defaults` replaces the complete workspace override
record. Omitting either field and explicitly setting it to `null` have the same
meaning: inherit that dimension.

```http
PUT /api/v1/workspaces/defaults
X-Workspace-ID: workspace-acme
Content-Type: application/json
```

```json
{
  "model_target": {
    "linked_service_id": "linked-service-openai-primary",
    "model_id": "gpt-5"
  },
  "harness": {
    "kind": "louie",
    "version": "v1",
    "config": {}
  }
}
```

The response has the same shape as `GET`. The endpoint returns
`422 linked_service_selection_unavailable` when the model target cannot be
served by the selected workspace linked service.

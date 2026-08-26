# Workspaces

Users own Workspaces. Creating a Workspace creates an `owner` membership for
the requesting User. The first Workspace owned by a User becomes its default;
later Workspaces require `X-Workspace-ID` when the User needs to select one.

Workspace defaults store optional `model_id` and Harness overrides for the
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
| `GET` | `/api/v1/workspaces/{workspace_id}` | Describe one accessible Workspace. |
| `PATCH` | `/api/v1/workspaces/{workspace_id}` | Update one accessible Workspace. |
| `GET` | `/api/v1/workspaces/{workspace_id}/defaults` | Describes workspace default overrides. |
| `PUT` | `/api/v1/workspaces/{workspace_id}/defaults` | Replaces all workspace default overrides. |

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

## Describe workspace

`GET /api/v1/workspaces/{workspace_id}` returns one Workspace accessible to
the User identified by `X-User-ID`.

```http
GET /api/v1/workspaces/workspace-acme
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "workspace-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Update workspace

`PATCH /api/v1/workspaces/{workspace_id}` updates mutable metadata for one
Workspace accessible to the User identified by `X-User-ID`. Currently, `name`
is the only mutable field, and it must be supplied with a non-empty value.

```http
PATCH /api/v1/workspaces/workspace-acme
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "Acme Platform"
}
```

Example response (`200 OK`):

```json
{
  "id": "workspace-acme",
  "name": "Acme Platform",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:15:00Z"
}
```

`model_id` selects one logical catalog model. `harness` selects one supported
local execution mechanism. Both fields are nullable; `null` means inherit
rather than choose a workspace override. For `louie`, run creation requires an
effective model ID, selects the first deterministically ordered compatible,
enabled, configured Linked Service, and freezes a private internal snapshot.
`codex_cli` does not select API Linked Services or require API provider
credentials.

## Describe workspace defaults

`GET /api/v1/workspaces/{workspace_id}/defaults` returns the specified
accessible workspace's stored overrides. A workspace with no configured record
returns both values as `null`.

```http
GET /api/v1/workspaces/workspace-acme/defaults
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "model_id": "gpt-5",
  "harness": {
    "kind": "codex_cli",
    "version": "v1",
    "config": {}
  },
  "updated_at": "2026-08-25T10:00:00Z"
}
```

## Replace workspace defaults

`PUT /api/v1/workspaces/{workspace_id}/defaults` replaces the complete
workspace override record. Omitting either field and explicitly setting it to
`null` have the same meaning: inherit that dimension.

```http
PUT /api/v1/workspaces/workspace-acme/defaults
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "model_id": "gpt-5",
  "harness": {
    "kind": "louie",
    "version": "v1",
    "config": {}
  }
}
```

The response has the same shape as `GET`.

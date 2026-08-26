# Workspaces

Users own Workspaces. Creating a Workspace creates an `owner` membership for
the requesting User. The first Workspace owned by a User becomes its default;
later Workspaces require `X-Workspace-ID` when the User needs to select one.

Workspaces select placement for Pipeline and Activity runs. Model and Harness
defaults belong to User settings; Pipeline, Activity, and loop-agent
configuration can define narrower persisted overrides.

## Workspace calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/workspaces` | List Workspaces accessible to the current User. |
| `POST` | `/api/v1/workspaces` | Create a Workspace owned by the current User. |
| `GET` | `/api/v1/workspaces/{workspace_id}` | Describe one accessible Workspace. |
| `PATCH` | `/api/v1/workspaces/{workspace_id}` | Update one accessible Workspace. |

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

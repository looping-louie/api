# Projects

Users own Projects. Creating a Project creates an `owner` membership for the
requesting User. The first Project owned by a User becomes its default;
later Projects require `X-Project-ID` when the User needs to select one for
execution placement.

Projects select placement for Pipeline and Activity runs. Model and Harness
defaults belong to User settings; Pipeline, Activity, and loop-agent
configuration can define narrower persisted overrides.

## Project calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/projects` | List Projects accessible to the current User. |
| `POST` | `/api/v1/projects` | Create a Project owned by the current User. |
| `GET` | `/api/v1/projects/{project_id}` | Describe one accessible Project. |
| `GET` | `/api/v1/projects/{project_id}/workers` | List Workers enabled for one Project. |
| `PATCH` | `/api/v1/projects/{project_id}` | Update one accessible Project. |

## List projects

`GET /api/v1/projects` returns every Project accessible to the User identified
by `X-User-ID`. The default Project appears first.

```http
GET /api/v1/projects
X-User-ID: user-123
```

Example response (`200 OK`):

```json
[
  {
    "id": "project-acme",
    "name": "Acme",
    "created_at": "2026-08-26T10:00:00Z",
    "updated_at": "2026-08-26T10:00:00Z"
  }
]
```

## Create project

`POST /api/v1/projects` creates a Project owned by the User identified by
`X-User-ID`. The User must first be registered through `POST /api/v1/users`.

```http
POST /api/v1/projects
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
  "id": "project-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Describe project

`GET /api/v1/projects/{project_id}` returns one Project accessible to
the User identified by `X-User-ID`.

```http
GET /api/v1/projects/project-acme
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "project-acme",
  "name": "Acme",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## List Project Workers

`GET /api/v1/projects/{project_id}/workers` returns the Workers enabled to
claim work for one accessible Project. Each item combines Worker identity and
observed Harness state with that Project's enablement. `enabled_at` belongs to
the enablement association, not to the Worker itself. `active_claims` counts
the Worker's active leases across all enabled Projects; `capacity` is currently
fixed at `1`. The response does not expose enablements in other Projects.

```http
GET /api/v1/projects/project-acme/workers
X-User-ID: user-123
```

## Update project

`PATCH /api/v1/projects/{project_id}` updates mutable metadata for one Project
accessible to the User identified by `X-User-ID`. Currently, `name`
is the only mutable field, and it must be supplied with a non-empty value.

```http
PATCH /api/v1/projects/project-acme
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
  "id": "project-acme",
  "name": "Acme Platform",
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:15:00Z"
}
```

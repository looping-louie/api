# Users

Users are durable top-level identities. Authentication is not implemented yet;
clients identify the acting user with `X-User-ID`. The User resource has no
profile fields beyond execution settings. Its `settings.default_harness` value
is inherited by owned Pipeline and Activity runs when no narrower Harness is
configured.

## Resource endpoints

| Method | Path | Purpose |
| ------ | ---- | ------- |
| `GET` | `/api/v1/users/me` | Return the registered current user. |
| `POST` | `/api/v1/users` | Register the current user if it is new. |
| `PATCH` | `/api/v1/users/me` | Replace current-user execution settings. |

## Register the current user

`POST /api/v1/users` persists the identity supplied in `X-User-ID`. Repeated
requests are idempotent and preserve the original timestamps.

```http
POST /api/v1/users
X-User-ID: user-123
```

Example response (`201 Created`):

```json
{
  "id": "user-123",
  "settings": {
    "default_harness": null
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Get the current user

`GET /api/v1/users/me` returns the user identified by `X-User-ID`. It returns
`404 user_not_found` until that identity has been registered.

```http
GET /api/v1/users/me
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "id": "user-123",
  "settings": {
    "default_harness": null
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:00:00Z"
}
```

## Update user settings

`PATCH /api/v1/users/me` replaces the User's execution settings. A `null`
`default_harness` clears the User-level override. A configured value is used
only after Activity, Pipeline, and Workspace Harness candidates are absent.

```http
PATCH /api/v1/users/me
X-User-ID: user-123
Content-Type: application/json

{
  "default_harness": {
    "kind": "codex_cli"
  }
}
```

Example response (`200 OK`):

```json
{
  "id": "user-123",
  "settings": {
    "default_harness": {
      "kind": "codex_cli",
      "version": "v1",
      "config": {}
    }
  },
  "created_at": "2026-08-26T10:00:00Z",
  "updated_at": "2026-08-26T10:05:00Z"
}
```

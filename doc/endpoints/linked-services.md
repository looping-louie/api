# Linked Services

Linked Services are User-owned, independently named provider connections.
Several services can use the same curated provider type.

## Linked service calls

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET` | `/api/v1/linked-services` | Lists User-owned linked services. |
| `POST` | `/api/v1/linked-services` | Creates and tests a linked service. |
| `GET` | `/api/v1/linked-services/{service_id}` | Describes one linked service. |
| `PATCH` | `/api/v1/linked-services/{service_id}` | Updates mutable settings. |
| `DELETE` | `/api/v1/linked-services/{service_id}` | Deletes one linked service. |

`service_id` is immutable. `name`, `enabled`, and `config` are mutable.
`provider_type` must be one of the curated provider identifiers. `config.api_key`
is write-only; responses return `base_url`, `key_trimmed`, `configured`, and
static `available_models` derived from active logical catalog models. Available
models are never stored in the linked-services table.

## List linked services

`GET /api/v1/linked-services` returns every linked service owned by the User
identified by `X-User-ID` as a JSON array. Linked Service routes ignore
`X-Workspace-ID`.

```http
GET /api/v1/linked-services
X-User-ID: user-123
```

Example response (`200 OK`):

```json
[
  {
    "id": "linked-service-openai-primary",
    "name": "primary_openai",
    "provider_type": "openai",
    "enabled": true,
    "config": {
      "base_url": "https://api.openai.com/v1",
      "key_trimmed": "sk-...abcd",
      "configured": true,
      "available_models": [
        "gpt-5"
      ]
    },
    "version": 1,
    "created_at": "2026-08-13T10:00:00Z",
    "updated_at": "2026-08-13T10:00:00Z"
  }
]
```

## Create a linked service

`POST /api/v1/linked-services` creates a named service and tests its candidate
configuration before it is stored. `enabled` defaults to `true`. A provider
that requires credentials must receive a usable `config.api_key` before it can
be enabled. The service belongs to the User identified by `X-User-ID`.

```http
POST /api/v1/linked-services
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "name": "primary_openai",
  "provider_type": "openai",
  "enabled": true,
  "config": {
    "api_key": "provider-api-key",
    "base_url": "https://api.openai.com/v1"
  }
}
```

Example response (`201 Created`):

```json
{
  "id": "linked-service-openai-primary",
  "name": "primary_openai",
  "provider_type": "openai",
  "enabled": true,
  "config": {
    "base_url": "https://api.openai.com/v1",
    "key_trimmed": "sk-...abcd",
    "configured": true,
    "available_models": [
      "gpt-5"
    ]
  },
  "version": 1,
  "created_at": "2026-08-13T10:00:00Z",
  "updated_at": "2026-08-13T10:00:00Z"
}
```

## Describe a linked service

`GET /api/v1/linked-services/{service_id}` returns one service owned by the
identified User. The response has the same shape as a list item and never includes
the full API key.

```http
GET /api/v1/linked-services/linked-service-openai-primary
X-User-ID: user-123
```

The endpoint returns `404 linked_service_not_found` when the User does not own
`service_id`.

## Update a linked service

`PATCH /api/v1/linked-services/{service_id}` accepts one or more of `name`,
`enabled`, or `config`. Supplying `config.api_key: null` clears the stored key;
supplying `config.base_url: null` restores the provider default. `enabled` must
be a boolean when supplied. Configuration changes and enabling a disabled
service validate and test the candidate connection before storage.

```http
PATCH /api/v1/linked-services/linked-service-openai-primary
X-User-ID: user-123
Content-Type: application/json
```

```json
{
  "enabled": false
}
```

The endpoint returns the updated linked-service response (`200 OK`). An empty
request returns `422`.

## Delete a linked service

`DELETE /api/v1/linked-services/{service_id}` removes a service that is not
referenced by another User-owned resource.

```http
DELETE /api/v1/linked-services/linked-service-openai-primary
X-User-ID: user-123
```

Example response (`200 OK`):

```json
{
  "deleted": true
}
```

The endpoint returns `409 resource_in_use` while another User-owned resource
still references the service, and `404 linked_service_not_found` when the
service does not exist for the identified User.

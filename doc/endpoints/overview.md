# API Endpoint Overview

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting loop-run checkpoints.

The API owns planning, generation, and reviewer decisions. The CLI owns local
repository execution, including filesystem, Git, and workspace lifecycle
operations.

## Endpoint reference

- [Providers](providers.md) manages model-provider configuration.
- [Models](models.md) exposes the curated model catalog.
- [Personas](personas.md) manages persona instructions.
- [Skills](skills.md) manages skill instructions.
- [Activities](activities.md) manages reusable concrete Activity definitions
  and their Activity runs.
- [Pipelines](pipelines.md) manages ordered Activity definitions and persists
  each supplied step as an independent Activity record.

## Versioned API conventions

All provider, model, persona, skill, activity, and pipeline routes use the
`/api/v1` prefix.

These routes require an authenticated user. In local development,
`LOUIE_DEV_AUTH=true` injects `LOUIE_DEV_USER_ID` as that user. A request may
select one of the user's workspaces with the optional `X-Workspace-ID` header.
If the user has access to more than one workspace and the header is omitted,
the API returns `409 workspace_selection_required`.

List operations return an object with `items` and `total`, except
`GET /api/v1/providers`, which returns a JSON array. The optional `search`
query parameter accepted by resource lists is case-insensitive and must contain
between 1 and 200 characters. Activity and activity-changelog lists accept a
non-negative `offset` and always return at most ten items. Pipeline lists also
use fixed ten-item pages, support `status` and `search`, and exclude archived
pipelines unless `status=archived` is requested.

Create operations return `201 Created`. Persona and skill content updates use
optimistic concurrency and require the current positive integer
`expected_version`; activity updates do not.

## Shared Field Formats

The following format applies to every `name` field on Activity, Pipeline, and
Persona create and update requests, including inline Activity definitions in a
Pipeline.

| Field | JSON type | Required | Restrictions |
| ----- | --------- | -------- | ------------ |
| `name` | String | Yes on create; no on update | Contains 1 to 140 characters. Starts with a Unicode letter, number, or `_`. Does not contain whitespace, `.`, `+`, `?`, `/`, `<`, `>`, `*`, `%`, `&`, or `:`. |

Successful deletes return:

```json
{
  "deleted": true
}
```

Domain errors use this envelope:

```json
{
  "error": {
    "code": "version_conflict",
    "message": "The resource has changed.",
    "details": {
      "expected_version": 1,
      "current_version": 2
    }
  }
}
```

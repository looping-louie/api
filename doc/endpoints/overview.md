# API Endpoint Overview

Looping Louie API exposes a versioned API for managing the resources used by
the execution runtime and for persisting loop-run checkpoints.

The API owns planning, generation, and reviewer decisions. The CLI owns local
repository execution, including filesystem, Git, and workspace lifecycle
operations.

## Endpoint reference

- [Catalog](catalog.md) exposes static provider, model, built-in Persona, and
  built-in Skill definitions.
- [Users](users.md) registers and retrieves the current API user.
- [Linked Services](linked-services.md) manages User-owned provider
  connections.
- [Workspaces](workspaces.md) manages User-owned Workspaces, their execution
  defaults, and model availability.
- [Personas](personas.md) manages persona instructions.
- [Skills](skills.md) manages skill instructions.
- [Activities](activities.md) manages User-owned reusable concrete Activity
  definitions and their Workspace-placed Activity runs.
- [Pipelines](pipelines.md) manages User-owned ordered Activity definitions and
  persists each supplied step as an independent User-owned Activity record.

## Versioned API conventions

All catalog, linked-service, workspace, model, persona, skill,
activity, and pipeline routes use the `/api/v1` prefix.

These routes require a user identity. Until authentication is implemented,
clients provide it through `X-User-ID`. In local development,
`LOUIE_DEV_AUTH=true` injects `LOUIE_DEV_USER_ID` when the request does not
already have an identity. A request may select one of the user's workspaces
with the optional `X-Workspace-ID` header when it targets a header-selected
Workspace resource. Workspace-addressed resources, including Model routes,
instead include the Workspace identifier in their URL and ignore that header.
If the user has access to more than one workspace and the header is omitted,
the API returns `409 workspace_selection_required`.

Persona, Skill, Linked Service, standalone Activity, and Pipeline definition
routes are user-scoped: their custom definitions, enablement settings, provider
connections, Activity definitions, and Pipeline definitions belong to
`X-User-ID`, and they ignore `X-Workspace-ID`.

Persona, Skill, Activity, Pipeline, User Model, and catalog Model lists
return an object with `items` and `total`. Catalog provider, built-in Persona,
and built-in Skill lists, plus linked-service lists, return JSON arrays. The
optional `search` query parameter accepted by resource lists is case-insensitive
and must contain between 1 and 200 characters. Activity and activity-changelog
lists accept a non-negative `offset` and always return at most ten items.
Pipeline lists also use fixed ten-item pages, support `status` and `search`, and
exclude archived pipelines unless `status=archived` is requested.

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

# Repository Instructions

These instructions apply to the entire repository. Follow more specific
`AGENTS.md` files if they are added in subdirectories.

## Core Principle

Implement exactly the behavior requested by the user, using the smallest
coherent change that satisfies the request.

- MUST NOT add speculative features, endpoints, validations, configuration,
  compatibility layers, abstractions, or refactors.
- MUST NOT change unrelated code merely because it could be improved.
- MUST NOT turn a focused task into an architectural redesign.
- MAY mention useful out-of-scope improvements in the final response, but MUST
  NOT implement them without explicit authorization.
- MUST reuse an established project pattern before introducing a new one.
- MUST NOT add or upgrade a dependency unless the requested behavior requires
  it.
- MUST ask before making a materially different product or architecture
  decision that cannot be inferred safely from the repository.

## Technology and API Style

This project is a Python FastAPI REST API.

- MUST use FastAPI and Pydantic conventions already present in the repository.
- MUST add type hints to every function and method.
- MUST define explicit Pydantic request and response schemas for HTTP
  contracts; do not return untyped dictionaries when a clear schema exists.
- MUST use an explicit `response_model` for endpoints when a response body is
  returned.
- MUST use HTTP methods, status codes, and error responses according to their
  REST semantics.
- MUST preserve existing public API contracts unless the user explicitly asks
  to change them.
- MUST NOT expose persistence entities directly through the HTTP API.
- SHOULD use plural nouns for resource collections and follow the existing URL
  conventions.
- MUST NOT introduce pagination, filtering, versioning, or other API behavior
  unless requested or required by an existing project convention.

## MVC and Layer Responsibilities

Apply MVC proportionally to the complexity of the change. Do not create empty
layers merely to satisfy a directory structure.

- **Model:** domain models and persistence-related entities.
- **View:** Pydantic request/response schemas and HTTP representations.
- **Controller:** application-facing orchestration between the HTTP layer and
  business services.
- **Router:** FastAPI route declarations and HTTP-specific concerns.
- **Service:** non-trivial or reusable business logic.
- **Repository:** persistence and data-access logic.

Dependency flow should normally be:

`router -> controller -> service -> repository`

The following constraints apply:

- Routers and controllers MUST remain thin.
- Routers MUST handle routing, dependency injection, request extraction, and
  response declaration.
- Controllers MUST coordinate use cases and translate application results for
  the HTTP layer.
- Business rules MUST live in services when they are non-trivial or reusable.
- Database queries and persistence details MUST live in repositories.
- Services MUST NOT depend on FastAPI request or response objects.
- Repositories MUST NOT contain HTTP concerns.
- Layers MAY be omitted when they add no meaningful separation.
- MUST NOT add a service, repository, interface, factory, or helper solely for
  hypothetical future reuse.

## File Size

Handwritten Python source and test files MUST contain no more than 300 physical
lines, including docstrings, comments, and blank lines.

- Generated files, database migrations, and snapshots are exempt.
- New files MUST comply with the limit.
- A modified file SHOULD be split by responsibility when it approaches the
  limit.
- Existing files over the limit are technical debt, not authorization for a
  repository-wide refactor.
- When the requested change touches an existing file over 300 lines, split the
  relevant responsibility if that can be done safely within scope. If doing so
  would require a broad unrelated refactor, keep the requested change narrow,
  do not increase the file's line count unnecessarily, and report the
  pre-existing violation.
- MUST NOT compress formatting, combine unrelated responsibilities, or remove
  useful documentation merely to satisfy the limit.

## Documentation

Use concise, informative documentation in English.

- Every Python module, including test modules and `__init__.py` files, MUST
  have a module docstring.
- Every class, function, method, and test function MUST have a docstring.
- Use Google-style docstrings consistently for parameters, return values,
  raised exceptions, and other contract details when they are not obvious.
- A docstring MUST explain purpose or contract information that is not already
  obvious from the name and type signature.
- Inside functions, add brief comments at meaningful decision points to
  explain why an invariant, branch, workaround, or non-obvious operation is
  necessary.
- Comments MUST explain intent and reasoning, not narrate straightforward code.
- MUST NOT add redundant comments to every line or restate the implementation
  in prose.

## Tests

Every behavior change MUST include or update corresponding tests.

- Test observable behavior and public contracts rather than implementation
  details.
- Add unit tests for business logic and integration or router tests for HTTP
  behavior as appropriate.
- Cover the requested success path and relevant error or boundary cases.
- Every bug fix MUST include a regression test that fails without the fix.
- Mock external boundaries when needed; do not mock the behavior under test.
- MUST NOT delete, skip, weaken, or rewrite assertions merely to make the test
  suite pass.
- MUST NOT make tests depend on execution order, network access, or shared
  mutable state unless the test explicitly covers such an integration.
- Test code follows the same 300-line and documentation rules as production
  code.

## Development Workflow

Before editing:

1. Read the relevant implementation and tests.
2. Identify the smallest set of files and responsibilities involved.
3. Check for existing conventions before creating a new pattern.

During implementation:

1. Make one coherent change at a time.
2. Run the most relevant focused tests after each coherent change.
3. Keep production code, tests, schemas, and documentation synchronized.
4. Avoid unrelated formatting, renames, cleanup, and import reordering.

Before declaring the work complete:

1. Review the diff for accidental scope expansion.
2. Confirm that new and modified code follows the architecture, size,
   documentation, and testing rules above.
3. Run the full suite from the repository root:

   ```bash
   pytest -q
   ```

4. Report the exact verification result. MUST NOT claim that tests pass if the
   command was not run successfully.

If the full suite fails:

- Investigate whether the change caused the failure.
- Fix failures caused by the requested change.
- Do not expand the task to fix unrelated, pre-existing failures.
- Clearly distinguish pre-existing failures from newly introduced failures.
- Ask before repairing unrelated failures if doing so would expand the scope.

## Definition of Done

A task is complete only when:

- The requested behavior is implemented without unrequested functionality.
- Layer responsibilities remain clear and no speculative abstraction was
  introduced.
- New files respect the 300-line limit, and touched legacy violations were
  handled according to the file-size policy.
- Modules, classes, functions, methods, and tests have useful docstrings.
- Non-obvious implementation decisions have concise `why` comments.
- Corresponding tests were added or updated.
- `pytest -q` was run and its outcome was reported accurately.
- Existing API contracts and unrelated behavior remain intact.

## Communication

Keep progress updates and final responses concise and outcome-oriented.

- Lead with what changed or what was found.
- Explain implementation details only when they affect correctness, security,
  compatibility, or a decision the user must make.
- The final response SHOULD state the changed behavior, tests run and their
  result, and any genuine limitation or follow-up decision.
- MUST NOT provide a lengthy work diary or repeat information unnecessarily.

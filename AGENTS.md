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

Handwritten Python source and test files SHOULD NOT contain more than 400
physical lines, including docstrings, comments, and blank lines. New or
modified files MUST NOT contain more than 800 physical lines under any
circumstances.

- Generated files, database migrations, and snapshots are exempt.
- New files SHOULD stay within 400 lines. They MAY exceed that target when
  keeping one cohesive responsibility together is clearly safer than splitting
  it, but they MUST remain within the absolute 800-line limit.
- A modified file SHOULD be split by responsibility when it approaches or
  exceeds 400 lines and doing so is safe and proportionate to the task.
- Existing files over 400 lines are technical debt, not authorization for a
  repository-wide refactor.
- When the requested change touches an existing file over 400 lines, split the
  relevant responsibility if that can be done safely within scope. If doing so
  would require a broad unrelated refactor, keep the requested change narrow,
  do not increase the file's line count unnecessarily, and report the
  pre-existing violation.
- No new or modified handwritten Python source or test file may exceed 800
  physical lines.
- MUST NOT compress formatting, combine unrelated responsibilities, or remove
  useful documentation merely to satisfy either threshold.

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
- doc/backlog operates kind of like a document-based project manager; so, its
  files SHOULD NOT be edited once created, unless strictly necessary.
- doc/architecture.md and doc/API.md are extremely important files which
  describe the whole project. So, they MUST be kept continuously up-to-date.
  Whenever a change is made to some file that might impact on its content, it
  should be updated.

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

### SQLite Migrations

SQLite migration files are immutable once committed. Do not edit an existing
migration for any reason, including whitespace or terminal-newline changes.
Create a new forward migration instead.

Every new SQLite migration must be added to
`tests/integration/test_sqlite_migration_checksums.py`. That test protects the
exact bytes of committed migrations and must pass before the migration is
committed.

Before editing:

1. Read the relevant implementation and tests.
2. Identify the smallest set of files and responsibilities involved.
3. Check for existing conventions before creating a new pattern.

During implementation:

1. Make one coherent change at a time.
2. Run the most relevant focused tests after each coherent change.
3. Keep production code, tests, schemas, and documentation synchronized.
4. Avoid unrelated formatting, renames, cleanup, and import reordering.

### Development Servers and Runtime Artifacts

- MUST NOT start `make dev`, `make run`, Uvicorn, or another long-lived API
  server through a sandboxed agent terminal. Sandboxed environments can create
  empty home-configuration placeholders such as `.bashrc`, `.gitconfig`, or
  `.vscode` in the repository root.
- MUST ask the user to start long-lived servers from a normal integrated
  terminal, or reuse an already-running local server for API/CLI validation.
- MUST remove only verified empty sandbox placeholders if they appear; do not
  add them to `.gitignore` because that hides the underlying execution issue.
- `runtime/db/looping-louie.db` is the intentional ignored local
  SQLite runtime database. It is distinct from the unwanted placeholders.

Before declaring the work complete:

1. Review the diff for accidental scope expansion.
2. Confirm that new and modified code follows the architecture, size,
   documentation, and testing rules above.
3. Run the full suite from the repository root using the project virtual
   environment:

   ```bash
   env/bin/python -m pytest -q
   ```

   - Do not use bare `pytest`; it is not installed in the system environment.
   - Do not use `make test` for routine verification because its `venv`
     prerequisite reinstalls dependencies.
   - In Codex environments, request execution outside the sandbox for tests
     that use `aiosqlite`; they can stall inside the sandbox.
   - If the suite makes no progress for 30 seconds, interrupt it and rerun the
     affected test with `-vv -s -o faulthandler_timeout=10`.

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
- New and modified files follow the 300-line target and absolute 500-line
  limit, and touched legacy violations were handled according to the file-size
  policy.
- Modules, classes, functions, methods, and tests have useful docstrings.
- Non-obvious implementation decisions have concise `why` comments.
- Corresponding tests were added or updated.
- `env/bin/python -m pytest -q` was run and its outcome was reported
  accurately.
- Existing API contracts and unrelated behavior remain intact.

## Communication

Keep progress updates and final responses concise and outcome-oriented.

- Lead with what changed or what was found.
- Explain implementation details only when they affect correctness, security,
  compatibility, or a decision the user must make.
- The final response SHOULD state the changed behavior, tests run and their
  result, and any genuine limitation or follow-up decision.
- MUST NOT provide a lengthy work diary or repeat information unnecessarily.

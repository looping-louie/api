---
id: nuxt
name: Nuxt Development Review
category: code_review
description: >
  Reviews Nuxt application changes for functional correctness, framework
  conventions, Vue integration, routing, SSR and hydration safety, data
  fetching, state management, Nitro APIs, security, SEO, performance,
  caching, deployment compatibility, type safety, and test coverage.
phase: code_review
artifacts:
  - git_diff
  - changed_files
output: json
---

# Nuxt Development Review

## Role

Review the candidate change as a production-minded Nuxt engineer.

Judge whether the patch:

- fulfils the original request and acceptance criteria;
- preserves the existing application architecture and public contracts;
- uses the Nuxt, Vue, Nitro, and H3 execution models correctly;
- remains safe across server rendering, hydration, client navigation, and direct
  server requests;
- avoids material regressions in security, privacy, SEO, accessibility,
  performance, resilience, deployment, and maintainability.

Judge outcomes and framework correctness, not personal style.

This skill is framework-specific. Apply a separate platform-level web review when
one is available, but do not assume another reviewer will catch Nuxt-specific
failures.

## Inputs

Use:

- the original request;
- the candidate Git diff;
- the changed-file contents;
- the project constitution, when supplied;
- any supplied review focus and strictness.

Use repository evidence such as:

- `package.json` and the lockfile;
- `nuxt.config.*`;
- `tsconfig.json` and generated-type references;
- the configured source and directory structure;
- app, server, shared, module, layer, and test files;
- deployment and environment configuration.

Do not claim that the project builds, type-checks, hydrates, deploys, or passes
runtime tests unless the artifacts provide that evidence.

## Precedence

Apply requirements in this order:

1. original request and explicit acceptance criteria;
2. project constitution;
3. installed Nuxt version and active compatibility settings;
4. established project architecture and conventions;
5. this skill.

## Version and configuration awareness

Before reviewing framework usage, infer the effective project model from the
repository.

Inspect, when available:

- the installed `nuxt` version in `package.json` or the lockfile;
- `future.compatibilityVersion` and experimental flags;
- `srcDir`, `rootDir`, `dir`, aliases, layers, and module configuration;
- whether the project uses universal rendering, `ssr: false`, prerendering, or
  route-level hybrid rendering;
- the Nitro deployment preset or intended host;
- whether TypeScript, Pinia, Nuxt Image, Nuxt Content, i18n, auth, or other
  modules are actually installed.

Nuxt 3 and Nuxt 4 projects may use different default directory layouts. Nuxt 3
commonly places `pages/`, `components/`, `composables/`, `plugins/`, `layouts/`,
and `assets/` at the source root. Nuxt 4 defaults to an `app/` directory. Either
can be valid when it matches the installed version and configuration.

Do not:

- reject valid Nuxt 3 code solely because it does not use Nuxt 4 paths;
- require a module, composable, directory, or feature that the project does not
  use;
- mark auto-imported Nuxt, Vue, component, composable, utility, or server symbols
  as missing imports without checking the generated conventions;
- recommend a migration or experimental feature unless the task requires it;
- treat a deprecation as a blocker when the installed version explicitly retains
  compatible behaviour and the patch does not worsen the migration risk.

If the effective version or rendering target cannot be determined and it changes
the verdict, report a verification gap instead of inventing a failure.

## Review boundaries

### Review the patch, not an imaginary rewrite

Concentrate on defects introduced by the change and on existing code that the
change directly depends on, exposes, or worsens.

Do not reject a focused patch because unrelated legacy code does not follow every
modern Nuxt recommendation.

### Apply only relevant checks

A check is applicable when the patch creates, changes, or depends on that surface.

Examples:

- Review hydration when code can execute during SSR and again in the browser.
- Review route rules when rendering, redirects, headers, caching, CORS, proxying,
  or prerendering changes.
- Review Nitro deployment compatibility when server code or native APIs change.
- Review SEO when public routes, rendering mode, page content, or head metadata
  change.
- Review cookie and session rules when authentication, persistence, or
  request-bound state changes.
- Review module and layer precedence only when modules, layers, aliases, or
  configuration are touched.

When a relevant property cannot be verified statically, report a warning. Do not
pretend to have run the application.

### Status meanings

- **Required**: fundamental Nuxt or application contract; a material violation
  may block.
- **Recommended**: expected when applicable; normally a warning or deduction.
- **Optional**: context-dependent; never penalise unless requested.
- **Avoid**: a known harmful, misleading, obsolete, or fragile pattern.

### Evidence rules

Every blocking issue must:

- identify the repository-relative file and nearest line or code location;
- describe the concrete failure mechanism;
- explain the user, security, data, crawler, build, deployment, or maintenance
  impact;
- state the smallest practical correction.

Do not double-count one root cause across several categories.

## Strictness

Use the planner-provided strictness. Default to `medium`.

### `low`

- Review the changed surface only.
- Block broken functionality, build-breaking framework usage, exploitable
  security flaws, data leaks, request-state leakage, destructive regressions,
  and serious SSR or hydration failures.
- Treat most maintainability and optimisation findings as warnings.

### `medium`

- Review the changed surface and its immediate Nuxt contracts.
- Enforce applicable Required and Avoid rules.
- Deduct for meaningful misuse of routing, fetching, state, caching, metadata,
  typing, or deployment behaviour.

### `high`

- Review for production or launch readiness using all relevant repository
  evidence.
- Enforce Required and Avoid rules strictly.
- Important Recommended rules may block when the task, constitution, deployment
  target, public traffic, authentication model, or acceptance criteria depend on
  them.
- Still do not penalise irrelevant features or demand a framework migration.

A supplied focus changes emphasis, not safety. Always report critical
cross-cutting defects.

## Review procedure

1. Determine the requested behaviour and affected user flows.
2. Detect the effective Nuxt version, directory model, rendering mode, modules,
   and deployment target.
3. Identify changed pages, layouts, components, composables, plugins,
   middleware, server handlers, shared code, configuration, assets, and tests.
4. Trace execution across initial SSR, payload serialisation, hydration, client
   navigation, direct API requests, and deployment runtime where applicable.
5. Select only the applicable checklist sections.
6. Separate blocking defects, warnings, and unverifiable concerns.
7. Score the patch from 0 to 100.
8. Return only the required JSON.

# Checklist

## 1. Functional correctness and integration — Required

- The requested behaviour and acceptance criteria are implemented.
- Routes, page names, layouts, middleware names, component contracts, composable
  APIs, plugin injections, runtime-config keys, server endpoints, and payload
  shapes remain consistent.
- New imports, dependencies, modules, and aliases resolve in the actual project
  context.
- Loading, empty, success, validation, unauthenticated, forbidden, not-found,
  and failure states are handled where relevant.
- The change does not introduce obvious duplicate submissions, stale state,
  request races, broken redirects, infinite navigation, unbounded watchers,
  repeated side effects, or data corruption.
- No mock data, debug logging, temporary bypass, placeholder secret, hard-coded
  environment value, or generated build output is accidentally committed.
- Existing build, lint, type-check, test, or formatting conventions are preserved
  or updated when the patch changes their contracts.

### Avoid

- Solving a Nuxt integration problem by bypassing the framework in a way that
  breaks SSR, routing, payload transfer, generated types, or deployment.
- Large unrelated refactors that obscure whether the requested change works.

## 2. Project structure and Nuxt configuration

### Required when applicable

- `nuxt.config.*` uses options supported by the installed Nuxt version.
- Configuration values that Nuxt or Nitro serialises are serialisable. Functions,
  class instances, `Map`, `Set`, clients, and other runtime objects live in
  plugins, modules, middleware, or runtime code instead of serialised config.
- Application, server, and shared code are placed in contexts where their imports
  can execute safely.
- `shared/` contains environment-neutral types and utilities and does not import
  Vue, Nuxt app context, Nitro request context, Node-only code, or browser-only
  code.
- `#server` imports remain inside the server context.
- `public/` is used for assets that must be served unchanged at stable root URLs.
  Build-processed assets are imported from the configured assets directory.
- `.nuxt/`, `.output/`, caches, local environment files, and other generated or
  secret-bearing artifacts are not treated as source files.
- Newly added modules and runtime dependencies appear in the appropriate package
  section and lockfile.

### Recommended when applicable

- Follow the configured default directory structure unless a custom structure has
  a clear project-wide purpose.
- Keep `nuxt.config.*` focused on declarative configuration; move substantial
  runtime logic into plugins, modules, or server code.
- Use `app.config.*` for public, reactive application configuration and theme-like
  values, not runtime secrets.
- Preserve layer and module override intent; project-level configuration should
  not accidentally erase required layer defaults.

### Avoid

- Assuming files in arbitrary nested plugin or module folders are auto-registered
  without checking Nuxt's scan rules.
- Referencing `~/assets/...` as a public runtime URL.
- Moving server-only libraries into app or shared code where they enter the
  client bundle.
- Putting secrets in `app.config`, `runtimeConfig.public`, `vite.define`, public
  environment variables, or client-visible source.

## 3. Vue components, composables, and reactivity

### Required

- Components expose coherent props, emits, slots, and model contracts.
- Props are not mutated directly.
- Reactive values are not accidentally destructured in a way that loses
  reactivity unless the active Vue/Nuxt compiler behaviour makes it safe.
- Watchers and subscriptions do not create loops, duplicate network requests, or
  retained listeners after unmount.
- Browser DOM access, observers, media queries, storage, and third-party widgets
  are initialised and cleaned up in the appropriate client lifecycle.
- Composables that require Nuxt context are called in a valid Nuxt context.
- Async custom composables do not lose the Nuxt instance by calling contextual
  composables after an arbitrary `await` unless the project explicitly supports
  that pattern.
- Component and composable names do not collide with compiler-reserved Nuxt names
  such as `useFetch`, `useAsyncData`, or `useState`.

### Recommended when applicable

- Prefer `<script setup>` and typed contracts when consistent with the project.
- Keep reusable business logic in composables or plain utilities rather than
  duplicating it across pages.
- Use plain utilities for logic that does not need Vue reactivity or Nuxt context.
- Use `shallowRef` or shallow async-data state for large immutable structures
  when deep reactivity is unnecessary.
- Lazy-load genuinely heavy or rarely used components instead of globally
  registering the entire component tree.
- Use `.client` components or `<ClientOnly>` for browser-only rendering and
  `.server` or island components only when supported and justified by the
  project.

### Avoid

- Wrapping broad sections of the application in `<ClientOnly>` merely to silence
  SSR errors.
- Calling composables conditionally in unstable execution paths when that breaks
  predictable setup behaviour.
- Global mutable singletons for per-user or per-request data.
- Importing browser-dependent packages at module top level in code evaluated on
  the server when the package has browser side effects.
- Enabling experimental islands, server components, delayed hydration, or native
  async context solely as a workaround for incorrect application logic.

## 4. Pages, layouts, routing, navigation, and route middleware

### Required when applicable

- File-based route names and dynamic parameters match the intended URLs for the
  installed Nuxt version.
- An application using pages renders `<NuxtPage>` through `app.vue`, a layout, or
  the framework's default entry.
- Nested parent pages render `<NuxtPage>` where child routes must appear.
- Layouts render page content through `<slot />` and satisfy the active Nuxt root
  requirements. A layout root is not only `<slot />` when transitions require a
  real root.
- `definePageMeta` is used only in page context and its middleware, layout,
  transition, keep-alive, validation, and custom metadata match registered names
  and expected types.
- Named route middleware names match Nuxt's kebab-case normalisation.
- Route middleware uses the supplied `to` and `from` routes rather than calling
  `useRoute()` to infer a current route.
- Redirects and aborted navigations are returned or awaited so navigation does
  not continue unpredictably.
- Middleware redirect logic cannot loop between protected and destination routes.
- Internal navigation preserves required params, query, hash, locale, and state.
- The Nuxt `useRoute()` implementation is used in app code when route-update
  timing matters; importing the identically named function from `vue-router`
  must not bypass Nuxt behaviour accidentally.
- Static files or cross-application URLs are not incorrectly sent through the
  client router.

### Security boundary

Route middleware is a user-experience navigation guard, not a trusted
application-security boundary.

- Protected data and mutations are authorised in Nitro, the upstream API, or
  another trusted server boundary.
- Hiding or redirecting a page does not count as protecting its server endpoint.
- Client-controlled route metadata, state, or cookies are not trusted as proof of
  authorisation.

### Recommended when applicable

- Use `<NuxtLink>` for internal application navigation and normal anchors or the
  `external` behaviour for files and external applications.
- Keep global middleware small because it runs on every navigation and may run in
  both server and client contexts.
- Preserve route names and public URLs unless the task includes a migration and
  redirects.
- Treat page-key, keep-alive, and transition changes as lifecycle changes and
  verify that state resets or persists intentionally.

### Avoid

- `window.location` for ordinary internal navigation.
- Importing or calling `useRoute()` inside route middleware.
- Relying on middleware execution order without explicit naming or project
  evidence.
- Using a page redirect as the only access-control mechanism.
- Nuxt 2 route filename and layout conventions in a Nuxt 3/4 project unless a
  compatibility layer explicitly handles them.

## 5. Universal rendering, SSR, hydration, and client-only behaviour

Apply this section to universal or hybrid routes and to any shared code that can
run on the server.

### Required

- Code evaluated during SSR does not access `window`, `document`, `navigator`,
  `localStorage`, `sessionStorage`, DOM constructors, or browser-only globals
  without an appropriate client boundary.
- Server and client produce compatible initial markup and initial reactive state.
- Initial render values do not diverge because of uncontrolled `Date.now()`,
  random values, timezone differences, browser dimensions, locale differences,
  client storage, or request-external mutable state.
- Per-request data is isolated. One user's session, headers, data, or feature
  state cannot leak into another request through module-scope reactive objects or
  singleton mutation.
- SSR-friendly state and data utilities transfer initial state through the Nuxt
  payload instead of recomputing incompatible values during hydration.
- Client-only side effects run after mount or behind a client-specific plugin or
  component boundary.
- Hydration warnings are not suppressed when the underlying mismatch affects
  content, interaction, or state.
- Browser-only libraries with top-level side effects are not imported by code
  bundled for the server.

### Recommended when applicable

- Use `useState` for small SSR-safe shared state, `useFetch` or `useAsyncData` for
  initial async data, and client lifecycle hooks for DOM-dependent behaviour.
- Provide useful `<ClientOnly>` fallback content or dimensions when omitting the
  server-rendered subtree would cause layout shift or missing primary content.
- Use `import.meta.client` and `import.meta.server`, or the established
  version-compatible project convention, for deliberate environment branches.
- Prefer deterministic server inputs such as request headers, cookies, and
  explicit locale over browser recomputation.

### Avoid

- Fixing a mismatch by disabling SSR for an entire public route without evaluating
  SEO, performance, and product requirements.
- Initialising the same event listener, analytics client, websocket, or SDK on
  both server and client.
- Module-level `ref`, `reactive`, store, or cache objects containing request-bound
  values.
- Rendering sensitive server values into HTML, the Nuxt payload, page props, or
  client state.

## 6. Data fetching and async data

### Choose the correct primitive

- Use `useFetch` for SSR-aware HTTP data needed by setup or initial rendering.
- Use `useAsyncData` for SSR-aware arbitrary async logic or for wrapping a custom
  client/query implementation.
- Use `$fetch` for event-driven interactions, mutations, client-only actions, or
  inside `useAsyncData` when appropriate.

Using bare `$fetch` for initial universal-rendered setup data can execute once on
the server and again during hydration because it does not transfer async state by
itself.

### Required

- Initial page data does not perform an avoidable duplicate server/client fetch.
- Async-data keys are stable, unique for the underlying resource and parameters,
  and do not collide across unrelated calls.
- Custom composables wrapping async data provide deterministic keys rather than
  relying on a wrapper's file-and-line auto-key.
- Calls sharing a key use compatible handlers, defaults, transforms, picks,
  cached-data functions, and deep/shallow behaviour.
- `useAsyncData` handlers return a defined non-null result when success is
  expected; nullish results do not accidentally trigger a second client fetch.
- Async-data handlers are side-effect free. Authentication mutation, store
  mutation, analytics, notifications, and other one-time effects use an
  intentional mechanism such as an event handler or `callOnce`.
- Reactive URLs, params, query values, bodies, headers, and other watched options
  do not cause unintended request storms.
- `server: false`, `lazy`, and `immediate: false` calls handle `idle`, `pending`,
  undefined data, errors, and explicit execution correctly.
- Requests that can become obsolete use Nuxt deduplication or the provided abort
  signal when the underlying client supports it.
- Errors are surfaced or transformed intentionally instead of silently producing
  misleading success UI.
- Mutation requests prevent duplicate destructive submission where required.
- Sensitive fields are not transferred to the client payload merely because the
  server response contained them.

### Request context and cookies

- Server-side calls that need the incoming user's cookies or selected headers use
  Nuxt's request-aware fetch behaviour or explicitly forward only required safe
  headers.
- Internal server-to-server calls use request context deliberately when downstream
  authentication depends on it.
- Incoming headers are not blindly proxied to external origins. Host,
  forwarding, content-length, infrastructure, and other unsafe headers are not
  leaked.
- Credentials are never forwarded to a destination whose origin is derived from
  untrusted input.

### Serialisation

- Values returned by Nitro API routes are compatible with JSON response
  serialisation or provide an explicit supported representation.
- The reviewer distinguishes Nuxt payload serialisation from API JSON
  serialisation; a value supported in the page payload may still change type when
  returned from a server endpoint.
- Dates, big integers, maps, sets, classes, errors, and custom domain objects are
  converted deliberately at API boundaries.

### Recommended when applicable

- Use `pick` or `transform` to reduce payload transfer when a response is much
  larger than the rendered data.
- Fetch independent resources in parallel rather than creating an avoidable
  waterfall.
- Use lazy fetching for secondary data only when the UI supplies an intentional
  loading state.
- Reuse keyed async data with `useNuxtData` where that matches cache semantics.
- Use a project-wide typed API client or `createUseFetch`/`createUseAsyncData`
  when repeated defaults would otherwise diverge.

### Avoid

- `useFetch` or `useAsyncData` inside arbitrary click handlers instead of `$fetch`
  or an existing async-data `execute`/`refresh` flow.
- Watchers that call `refresh` while the same reactive source already triggers
  automatic refetching.
- Reusing a constant key for requests whose URL, user, locale, tenant, or query
  changes.
- Storing entire upstream responses in the Nuxt payload when only a few fields are
  needed.
- Swallowing fetch errors and rendering empty data as a valid result.

## 7. State management, cookies, runtime config, and environment variables

### State — Required

- Shared state is request-safe during SSR.
- `useState` values are serialisable by the active Nuxt payload mechanism and do
  not contain functions, DOM nodes, service clients, or unsupported class
  instances without an explicit serializer.
- Keys identify one logical state value and do not collide across features.
- User, tenant, locale, permission, or request-specific state is not stored in a
  process-global singleton.
- Logout, account switching, tenant switching, and permission changes clear or
  recompute sensitive client state where required.
- A store used during SSR is integrated through a Nuxt-compatible mechanism and
  does not reuse one mutable store instance across requests.

### Cookies — Required when applicable

- Cookie state uses an SSR-aware mechanism in app code and request-aware H3
  utilities in server code.
- Authentication cookies are not made readable to client JavaScript unless the
  architecture explicitly requires it.
- Security-sensitive cookies use appropriate `Secure`, `HttpOnly`, `SameSite`,
  path, domain, expiry, and prefix rules.
- Cookie size and serialisation are bounded; large application objects are not
  persisted directly in cookies.
- Server changes that set cookies are reflected in the client state intentionally
  rather than leaving stale refs.

### Runtime config — Required

- Private runtime config stays outside `runtimeConfig.public` and is accessed only
  in trusted server code.
- Values required at runtime are declared in `runtimeConfig` and overridden using
  matching `NUXT_...` environment-variable names.
- The implementation does not rely on the development `.env` file being loaded by
  the built production server.
- Non-serialisable clients and functions are constructed in plugins or runtime
  code, not stored in runtime config.
- Server runtime config is treated as read-only request configuration.
- Private config is not rendered, logged, copied into `useState`, returned by an
  API, embedded in errors, or forwarded to the browser.

### Recommended when applicable

- Validate required environment variables during startup or the first trusted
  access and fail with a clear operational error.
- Type custom runtime-config keys when inference is insufficient.
- Keep build-time public app configuration distinct from deployment-time secrets.
- Store durable server state in a database or configured storage backend rather
  than process memory when the deployment can scale horizontally or restart.

### Avoid

- `process.env.OTHER_NAME` as the runtime default for a differently named config
  key when the value must change after build.
- Secrets in `NUXT_PUBLIC_*`, `app.config`, client plugins, page payloads, or
  browser storage.
- Assuming an in-memory Nitro cache or store is globally shared, durable, or
  consistent across serverless instances.

## 8. Nitro server routes, middleware, APIs, and trusted boundaries

### Required

- Server handlers export a valid `defineEventHandler`/`eventHandler` handler or
  the project-standard wrapper.
- HTTP methods are constrained through method-specific filenames or explicit
  checks; mutation handlers are not unintentionally callable with arbitrary
  methods.
- Route params, query values, headers, cookies, and request bodies are validated
  at runtime before trusted use.
- Authentication and authorisation are checked on the server for every protected
  resource and mutation.
- Object ownership, tenant boundaries, roles, and field-level permissions are
  enforced independently of client input.
- Invalid input produces an appropriate 4xx error; unexpected failures do not
  expose stack traces, credentials, SQL, file paths, or upstream internals.
- The handler returns a deliberate response body and status, or terminates the
  response intentionally.
- Server middleware inspects or extends the request and does not accidentally
  return a normal response, close the request, or replace route handling.
- Route middleware and server middleware are not confused.
- Dynamic external URLs, redirects, proxy destinations, file paths, and fetch
  targets are constrained against SSRF, open redirects, path traversal, and
  credential leakage.
- Cookie-authenticated state-changing endpoints address CSRF according to the
  application's origin and SameSite model.
- User-controlled HTML, SQL, shell arguments, templates, headers, and log fields
  are handled with context-appropriate safe APIs.
- Database or upstream failures do not leave partial destructive state without an
  intentional transaction or compensation strategy.

### Request forwarding

- `event.$fetch` is used when downstream internal handlers need the current
  request context and safe incoming headers.
- Ordinary `$fetch` is used when context forwarding is not desired.
- Forwarded headers are minimised, especially for external origins.
- The upstream base URL cannot be redirected by user-controlled host or URL data.

### Deployment compatibility

- Server code uses APIs supported by the configured Nitro preset and runtime.
- Node-only packages, filesystem writes, native binaries, long-lived sockets,
  background work, and process-local state are not assumed to work in edge or
  serverless targets without evidence.
- Work intended to continue after the response uses the provider-compatible
  mechanism when available and is not fire-and-forget in a runtime that may
  terminate immediately.

### Recommended when applicable

- Use validated H3 helpers for params, query, and bodies to align runtime
  validation with TypeScript types.
- Use reusable server utilities for authentication, validation, error mapping,
  and upstream clients without hiding control flow.
- Apply rate limits, idempotency, request-size limits, and timeouts to expensive
  or abuse-sensitive endpoints.
- Return stable typed DTOs rather than leaking database or SDK objects directly.
- Set explicit status codes for created, accepted, no-content, redirected, and
  partial responses.

### Avoid

- Trusting TypeScript types as runtime validation.
- Returning caught raw error objects as a successful `200` response.
- Performing authorisation only in a page or route middleware.
- Blindly spreading request headers into an upstream request.
- Caching private endpoint responses without a correct user or tenant partition.
- Using `readBody` on GET handlers or accepting mutation payloads on unconstrained
  routes without reason.

## 9. Errors, loading, recovery, and lifecycle resilience

### Required when applicable

- Missing public resources produce a real 404 path and status in the effective
  rendering/deployment model.
- Server handlers throw or return deliberate HTTP errors rather than masking
  failures as successful empty responses.
- Page and component failures do not leave endless spinners, disabled controls,
  duplicate submissions, stale success messages, or unrecoverable navigation.
- Error handling does not leak secrets or sensitive request data.
- The global error page or local error boundary provides a viable recovery path.
- Clearing a Nuxt error does not redirect into another failing route loop.
- User-entered form data is preserved after recoverable failures when practical.
- Cleanup logic accounts for Nuxt page transitions and Suspense behaviour, where a
  new page may mount before the previous page is fully unmounted.

### Recommended when applicable

- Distinguish validation, unauthenticated, forbidden, not-found, conflict,
  rate-limit, upstream, and internal errors in user and operational behaviour.
- Use local boundaries for recoverable component failures and the global Nuxt
  error flow for route-level or fatal failures.
- Add a loading indicator or skeleton only when it accurately represents the
  pending operation.
- Log enough server context to diagnose failures without logging credentials,
  tokens, full personal payloads, or secrets.
- Handle stale chunk or deployment-version failures according to the project's
  reload policy.

### Avoid

- Catching every error and returning `{ error }` with status 200.
- Calling `showError` or creating fatal errors for ordinary recoverable field
  validation.
- Infinite automatic retries or refresh loops.
- Relying on development overlays as production error handling.

## 10. SEO, head management, and public rendering

Apply primarily to public, indexable routes.

### Required when applicable

- The chosen rendering mode makes primary public content and metadata available
  to crawlers according to the product's indexing requirements.
- Each changed indexable route has a meaningful title and description strategy.
- Canonical, robots, social, alternate-language, and structured-data values match
  the actual route and content when the product uses them.
- Dynamic metadata is derived from the same canonical data as the rendered page
  and handles missing records and errors.
- User-controlled values do not enter unsafe head fields, raw script content, or
  HTML without an appropriate safe mechanism.
- Route changes do not leave stale metadata from the previous page.
- Private, authenticated, staging, error, duplicate, and thin routes are not
  unintentionally indexable.

### Nuxt-specific guidance

- Use `useSeoMeta` for typed SEO metadata.
- Use `useHead` for broader reactive head management.
- Use `useHeadSafe` when head data includes untrusted or user-generated values.
- Use static `app.head` configuration for truly global non-reactive tags when
  appropriate.
- `definePageMeta` defines route metadata; it is not a substitute for document
  title, description, canonical, or Open Graph tags.
- Static metadata need not remain client-reactive when only initial server output
  matters.

### Recommended when applicable

- Keep global defaults in one place and route-specific overrides close to page
  data.
- Generate absolute social-image and canonical URLs from trusted site
  configuration.
- Ensure public dynamic routes can be rendered or prerendered for every URL that
  must be indexed.
- Provide intentional metadata for 404 and error surfaces without creating soft
  404s.

### Avoid

- Raw `innerHTML` in head tags with untrusted content.
- Duplicated title, canonical, or description tags caused by unrelated head
  declarations.
- Disabling SSR globally for a public content site solely to simplify a browser
  integration.
- Treating client-only metadata updates as equivalent to initial crawlable head
  output when indexing is a requirement.

## 11. Performance, payload, assets, and client bundle

Do not claim measured Core Web Vitals or bundle reductions from a static diff.

### Required when applicable

- The patch does not introduce an obvious serial fetch waterfall for independent
  data.
- Large server responses, state objects, and unused fields are not unnecessarily
  serialised into the Nuxt payload.
- Heavy browser-only libraries do not enter the server bundle or every route's
  client bundle without need.
- Route-level code splitting is not defeated by eager imports or blanket global
  registration.
- Images and media reserve layout space and do not make the likely LCP resource
  lazy.
- Client-only fallbacks do not cause avoidable layout shift or hide essential
  initial content.
- Watchers, polling, route hooks, plugins, and event listeners do not multiply
  across navigation.
- Global plugins do not block startup with unrelated expensive work.
- Cache or prerender configuration does not serve stale or private data merely to
  improve speed.

### Recommended when applicable

- Parallelise independent server and page requests.
- Use lazy components for large below-the-fold or interaction-only features.
- Use Nuxt Image components only when the module is installed and its provider
  configuration is valid; otherwise use an appropriate native image strategy.
- Use build-processed assets for fingerprinting and optimisation, and `public/`
  for intentionally stable files.
- Limit payload fields with `pick` or `transform`.
- Use shallow state for large immutable collections.
- Use route rules, prerendering, SWR, or ISR only where freshness, personalisation,
  and deployment semantics permit.
- Inspect Nuxt DevTools, build analysis, server timing, or project benchmarks when
  the task explicitly targets performance.

### Avoid

- Blanket `ClientOnly`, `ssr: false`, or eager dynamic imports as performance
  fixes without measurement.
- Globally registering all components or importing every icon, locale, editor,
  chart, or SDK into the main bundle.
- Duplicate page fetching plus store fetching for the same initial resource.
- Preloading or prefetching every route and asset.
- Persisting huge reactive objects in cookies, payload state, or HTML.

## 12. Rendering modes, route rules, caching, prerendering, and deployment

### Rendering strategy

- Universal rendering, SPA rendering, prerendering, SWR, ISR, and edge rendering
  are architectural choices, not a quality ranking.
- A private back-office application may validly use `ssr: false`.
- A public content route may require server or static HTML for discoverability and
  initial performance.

### Required when applicable

- Rendering changes match the product requirements for SEO, authentication,
  freshness, interactivity, cost, and hosting.
- Route-rule globs target the intended pages or API routes and do not accidentally
  include sensitive neighbours.
- Redirect rules preserve status, params, query values, and destination intent.
- CORS is not enabled broadly when only selected origins, methods, or headers are
  trusted.
- Cached output is invariant for every request sharing the cache key.
- Authenticated, personalised, tenant-specific, locale-specific, experiment,
  permission, cookie, or header-dependent content is not cached as one public
  response without a correct variation strategy.
- Mutation endpoints, realtime data, one-time tokens, and sensitive responses are
  not cached.
- Cache freshness and invalidation match the underlying data lifecycle.
- Prerendered routes do not depend on runtime-only secrets or APIs unavailable at
  build time unless the build environment supplies them deliberately.
- Dynamic routes required in a static deployment are linked for crawling or
  explicitly included; the crawler cannot invent database-backed URLs.
- A fully static deployment does not depend on runtime Nitro endpoints, server
  sessions, or server-only modules that will not exist on the host.
- SPA fallback and real 404 behaviour match the hosting provider's rewrite rules.
- The built Nitro preset matches the actual deployment runtime.
- Production runtime variables are available under the names expected by Nuxt and
  Nitro.

### Recommended when applicable

- Use route-level hybrid rendering rather than globally sacrificing SSR or
  dynamism when requirements differ by area.
- Document unusual caching and invalidation assumptions near configuration.
- Test direct URL access, refresh, 404, redirects, cookies, and API behaviour in a
  production-like build.
- Treat in-memory cache as instance-local unless a shared storage driver is
  configured.
- Keep provider-specific configuration minimal and version-controlled.

### Avoid

- Caching a route merely because it is a GET request.
- Applying SWR/ISR to dashboards, account pages, session responses, or APIs that
  depend on request identity.
- Assuming `nuxt generate` discovers unlinked dynamic pages.
- Assuming code that works in the Node development server works unchanged on an
  edge runtime.
- Using a `200.html` SPA fallback for URLs that must preserve a real 404 status.

## 13. Plugins, modules, layers, auto-imports, and dependency order

### Plugins — Required when applicable

- Plugins are located where the active Nuxt configuration scans them, or are
  explicitly registered.
- Browser-only plugins use a client suffix or equivalent guard; server-only
  plugins do not enter the client build.
- Plugin injections are typed when consumed throughout a TypeScript project.
- Plugin order is not assumed accidentally. Dependencies use explicit project
  ordering, object-syntax names and `dependsOn`, or another stable mechanism.
- Parallel plugins do not depend on each other's completion.
- A composable called from a plugin does not depend on a later plugin.
- Plugin setup is idempotent where islands, tests, HMR, or multiple app instances
  can execute it more than once.

### Modules and layers — Required when applicable

- Added modules support the installed Nuxt version and selected rendering target.
- Module configuration keys match the installed module version.
- Module and layer order preserves intended overrides.
- Local modules use Nuxt Kit APIs rather than mutating generated files directly.
- Layer-relative paths, aliases, components, composables, and config merge as
  intended in both development and build.
- Runtime code required by a published layer or module is included in its package
  and not resolved accidentally from the host project's undeclared dependency.

### Auto-imports — Required when applicable

- Auto-imported symbols are available in the relevant app, server, or shared
  context.
- Name collisions do not silently bind to the wrong composable or utility.
- Explicit imports do not accidentally select a similarly named function from
  VueUse, Vue Router, another module, or a local library when Nuxt's version is
  required.
- Components in non-default directories are configured for scanning or imported
  explicitly.

### Recommended when applicable

- Prefer explicit dependencies over fragile alphabetical file naming when order is
  semantically important.
- Keep plugins small and cohesive.
- Use layers for genuinely reusable app structure rather than as an indirection
  for one local feature.
- Verify module release and compatibility notes before adopting new experimental
  behaviour.

### Avoid

- Adding plugins both through auto-registration and `nuxt.config`, causing double
  execution.
- Depending on nested plugin files being scanned when the installed version does
  not scan them.
- Importing Nuxt's `useRoute` from `vue-router` or Nuxt's `useFetch` from an
  unrelated package.
- Treating auto-import magic as a reason to ignore generated type or naming
  collisions.

## 14. TypeScript, generated types, linting, and build verification

### Required when applicable

- Changed TypeScript and Vue code remains compatible with the project's strictness
  and generated Nuxt types.
- Server, app, shared, node/config, and layer contexts use the correct type
  environment.
- Type augmentations are placed or included in the context where Nuxt's project
  references can see them.
- API route response and request types agree with runtime validation and actual
  serialised values.
- New aliases, modules, components, composables, plugin injections, and runtime
  config keys are represented in generated or augmented types.
- `tsconfig.json` does not replace Nuxt's generated recommendations in a way that
  removes aliases, auto-imports, server types, or project references.
- Generated `.nuxt` declaration files are not edited manually.

### Important verification rule

Nuxt does not necessarily type-check during ordinary `nuxt dev` or `nuxt build`.
A successful build claim is not proof of a clean type check unless the project's
build enables it or `nuxt typecheck`/`vue-tsc` evidence is supplied.

### Recommended when applicable

- Run or preserve a dedicated type-check script in CI.
- Use `nuxt prepare` before standalone editor, test, or type-check workflows that
  need generated files.
- Extend Nuxt TypeScript settings through supported configuration rather than
  copying generated config.
- Keep lint rules aligned with Vue SFC, Nuxt auto-import, and server contexts.
- Use inferred typed internal API routes where it improves correctness, while
  retaining runtime validation.

### Avoid

- Silencing errors with broad `any`, `as unknown as`, non-null assertions, or
  `@ts-ignore` without a documented invariant.
- Treating a TypeScript interface as proof that untrusted runtime input is valid.
- Committing `.nuxt` merely to make local types resolve.
- Importing app-only types into server or shared contexts through files that also
  execute runtime code.

## 15. Testing and regression protection

### Required when applicable

- Existing tests affected by route, component, composable, plugin, API, or config
  changes are updated.
- Security-sensitive server logic has coverage for unauthenticated, forbidden,
  invalid, and cross-tenant cases.
- Data-fetching tests cover loading, success, error, refetch, and reactive-key
  behaviour where those paths changed.
- SSR-sensitive changes have evidence that initial render and hydration agree,
  when the project has an established integration or E2E workflow.
- Deployment-mode changes are tested in a built or preview environment rather
  than only the development server when project conventions support it.

### Recommended when applicable

- Use plain unit tests for pure utilities.
- Use the Nuxt test environment for code that needs auto-imports, Nuxt context,
  plugins, runtime config, routing, or payload behaviour.
- Use E2E or browser tests for navigation, redirects, cookies, authentication,
  hydration, accessibility, and direct URL entry.
- Keep Nuxt runtime unit tests and full E2E setup in their appropriate test
  environments rather than mixing incompatible test-utils modes in one file.
- Assert user-visible behaviour and server contracts rather than framework
  implementation details.
- Add a regression test for every fixed defect when the repository already has a
  suitable test layer.

### Avoid

- Snapshot-only coverage for authentication, routing, hydration, or mutation
  correctness.
- Mocking Nuxt context so heavily that the test cannot detect incorrect runtime
  usage.
- Claiming SSR safety from a component test that never renders on the server.
- Making tests order-dependent through shared global state.

## 16. Migration, compatibility, and experimental features

### Required when applicable

- Migration code matches the source and target Nuxt versions.
- Nuxt 2 conventions such as `_id.vue`, `_.vue`, `<Nuxt>`, `<NuxtChild>`, legacy
  plugin context, or old middleware signatures are not introduced into a Nuxt
  3/4 application without an explicit compatibility mechanism.
- Nuxt 3-to-4 structure changes account for configured source directories,
  aliases, CSS paths, tests, layers, and deployment files.
- Removed or changed Unhead, Vue, Vite, Nitro, and module APIs are evaluated
  against the installed versions, not memory of another release.
- Compatibility flags that alter framework defaults are considered when judging
  routing, component names, async data, TypeScript, Vite environments, and
  plugin behaviour.

### Recommended when applicable

- Keep framework and module upgrades separate from unrelated product changes.
- Review official upgrade notes and module compatibility before changing major
  versions.
- Pin or constrain experimental/nightly dependencies according to the project's
  risk tolerance.
- Add migration tests for route names, metadata, payloads, server endpoints,
  generated output, and deployment behaviour.

### Avoid

- Recommending the newest API without checking whether it exists in the installed
  version.
- Enabling future compatibility or experimental flags to repair one local bug
  without assessing project-wide effects.
- Treating a warning-only deprecation as a production blocker when the current
  runtime supports it and the task is unrelated.
- Mixing Nuxt 2, Nuxt 3, Nuxt 4, and future-version examples in one implementation
  without a deliberate compatibility strategy.

# High-value Nuxt failure patterns

The following findings deserve particular attention because they are easy for a
weak reviewer to miss.

## Usually blocking when evidenced

- A private runtime secret is placed in `runtimeConfig.public`, app config, page
  state, payload data, browser storage, or returned API JSON.
- Per-user state is stored in a module-scope reactive singleton and can leak
  between SSR requests.
- A protected mutation is authorised only by route middleware or hidden UI.
- A cache or ISR/SWR route serves authenticated or tenant-specific output without
  correct partitioning.
- Browser-only code executes during SSR and crashes the route.
- Server and client initial output differ in a way that breaks hydration or user
  state.
- Initial data uses bare `$fetch` in universal setup and performs harmful duplicate
  requests or side effects.
- `useAsyncData` executes a mutation or side effect that can repeat on server and
  client.
- A static deployment still depends on Nitro APIs or server sessions.
- An edge deployment imports unsupported Node APIs or native dependencies.
- Server input is trusted from TypeScript alone and enables injection, SSRF,
  traversal, cross-tenant access, or destructive invalid mutation.
- A route middleware redirect loops or navigation continues because `navigateTo`
  was neither returned nor awaited.

## Usually warnings unless impact is demonstrated

- A valid Nuxt 3 project does not use the Nuxt 4 `app/` directory.
- A project uses explicit imports instead of auto-imports.
- A component uses the Options API in a project that supports it.
- A route uses `ssr: false` in a private application.
- A page does not use Nuxt Image when the module is absent.
- A small response does not use `pick` or `transform`.
- A recommended plugin, layer, island, server component, or experimental feature
  is not used.
- Type checking is not part of `nuxt build`, provided a separate valid type-check
  workflow exists.

# Scoring

Start at 100. Deduct only for evidenced and applicable findings.

Suggested deductions:

- **Critical: 30–60** — secret or personal-data exposure, cross-request state
  leak, authorisation bypass, cross-tenant access, exploitable server flaw,
  destructive corruption, public cache leak, or fundamentally non-working change.
- **Major: 12–29** — broken primary flow, build or deployment failure, serious SSR
  crash, persistent hydration failure, incorrect rendering architecture, broken
  routing, duplicate destructive request, major SEO regression, or material
  Required violation.
- **Moderate: 4–11** — meaningful but bounded framework misuse, error-state gap,
  avoidable duplicate fetch, stale state, type-safety regression, payload bloat,
  or fragile plugin/config behaviour.
- **Minor: 1–3** — small concrete issue with limited impact.
- **Optional improvement: 0** — mention only when genuinely useful and do not
  include it as a scored finding.

Score caps:

- Secret exposure, authorisation bypass, cross-request or cross-tenant data leak,
  or remotely exploitable server flaw: maximum 25.
- Broken primary flow, application build failure, deployment incompatibility,
  public private-data cache, or major SSR/hydration failure: maximum 49.
- Any unresolved blocking issue: maximum 69.
- No blockers and only minor warnings: normally 90 or above.

Interpretation:

- **90–100**: production-quality for the requested Nuxt scope.
- **75–89**: sound, with meaningful non-blocking improvements.
- **50–74**: substantial issues or at least one blocker.
- **25–49**: major failure or unsafe implementation.
- **0–24**: critically broken, dangerous, or unrelated.

Do not reduce the score for irrelevant Nuxt capabilities. Do not inflate the
score because the patch is small.

## Blocking threshold

A finding blocks when the patch should not be accepted before correction,
including:

- requested behaviour that does not work;
- a build-breaking or runtime-breaking Nuxt integration error;
- a material applicable Required violation;
- an Avoid pattern causing concrete harm;
- a security, privacy, authorisation, tenant-isolation, or data-integrity flaw;
- a cross-request state leak;
- a serious SSR, hydration, routing, caching, prerendering, or deployment
  regression;
- unintended deindexing of important public content or indexing of private
  content;
- broken project contracts, generated types, server APIs, or module integration.

Recommended items are normally non-blocking. Under `high` strictness they may
block when the request, constitution, public launch, deployment target, or
acceptance criteria depend on them.

# Output

Return JSON only, without Markdown and without additional keys:

{
  "score": 0,
  "blocking_issues": [
    "path/to/file.ext:line — [category] Concrete issue, impact, and required fix."
  ],
  "warnings": [
    "path/to/file.ext:line — [category] Concrete concern or verification gap and suggested improvement."
  ],
  "rationale": "Brief explanation of the score, effective Nuxt context, applicable areas reviewed, and strongest evidence."
}

Rules:

- `score` is an integer from 0 to 100.
- `blocking_issues` and `warnings` are always arrays.
- Use repository-relative paths and line numbers when available.
- Prefix findings with a useful category such as `[routing]`, `[hydration]`,
  `[data-fetching]`, `[state]`, `[runtime-config]`, `[server-security]`,
  `[caching]`, `[deployment]`, `[seo]`, `[types]`, or `[testing]`.
- Make every finding self-contained and actionable.
- Do not include praise, generic advice, style preferences, or optional wishlists
  as findings.
- Use an empty `blocking_issues` array when nothing blocks.
- Report insufficient evidence as a warning, not as an asserted failure.
- Mention the inferred Nuxt major version, directory model, rendering mode, or
  deployment target in `rationale` only when repository evidence supports it.
- Do not claim commands were run unless execution evidence was supplied.

# Source basis

This skill is an original review synthesis based primarily on the official Nuxt,
Nitro, H3, Vue, and Unhead documentation and adapted for diff-based automated
review.

Primary references:

- https://nuxt.com/docs/
- https://nuxt.com/docs/4.x/directory-structure
- https://nuxt.com/docs/4.x/getting-started/routing
- https://nuxt.com/docs/4.x/getting-started/data-fetching
- https://nuxt.com/docs/4.x/guide/best-practices/hydration
- https://nuxt.com/docs/4.x/guide/going-further/runtime-config
- https://nuxt.com/docs/4.x/getting-started/server
- https://nuxt.com/docs/4.x/getting-started/seo-meta
- https://nuxt.com/docs/4.x/guide/concepts/rendering
- https://nuxt.com/docs/4.x/getting-started/prerendering
- https://nuxt.com/docs/4.x/getting-started/deployment
- https://nuxt.com/docs/4.x/getting-started/testing
- https://nuxt.com/docs/4.x/guide/concepts/typescript
- https://nitro.build/docs/
- https://h3.dev/
- https://vuejs.org/guide/scaling-up/ssr.html
- https://unhead.unjs.io/

The reviewer must still prioritise the installed project version and repository
configuration over examples from any one documentation version.

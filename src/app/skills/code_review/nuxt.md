---
id: nuxt
name: Nuxt
category: framework_review
description: >
  Provides Nuxt-specific review knowledge for application structure, Vue
  integration, routing, rendering, hydration, data fetching, state, Nitro APIs,
  runtime configuration, caching, deployment, type safety, and testing.
phase: code_review
artifacts:
    - git_diff
    - changed_files
output: json
---

# Nuxt

## Scope

This skill covers framework-specific correctness in Nuxt applications.

It applies to changes involving:

- Nuxt application structure and configuration;
- Vue components, composables, plugins, and reactivity;
- pages, layouts, routing, navigation, and route middleware;
- server-side rendering, hydration, and client-only behaviour;
- async data, state, cookies, and runtime configuration;
- Nitro handlers, H3 utilities, and trusted server boundaries;
- rendering modes, route rules, caching, prerendering, and deployment;
- modules, layers, auto-imports, generated types, and testing.

Use the installed Nuxt version, active compatibility settings, repository
configuration, and deployment target as the source of truth.

## Project context detection

Determine the effective Nuxt model from repository evidence.

Inspect when available:

- the installed `nuxt` version in `package.json` or the lockfile;
- `future.compatibilityVersion` and experimental flags;
- `rootDir`, `srcDir`, `dir`, aliases, layers, and module configuration;
- whether the application uses universal rendering, `ssr: false`, prerendering,
  or route-level hybrid rendering;
- the Nitro preset and intended deployment runtime;
- whether TypeScript, Pinia, Nuxt Image, Nuxt Content, i18n, authentication, or
  other modules are installed;
- generated type references and project-specific conventions.

Nuxt 3 and Nuxt 4 may use different default directory layouts. Nuxt 3 commonly
places application directories at the source root, while Nuxt 4 defaults to an
`app/` directory. Either structure is valid when it matches the installed
version and configuration.

Do not treat the following as defects without repository evidence:

- Nuxt 3 directory conventions in a Nuxt 3 project;
- explicit imports instead of auto-imports;
- the Vue Options API;
- SPA rendering for a private application;
- absence of optional Nuxt modules;
- a supported API that is deprecated only in a later version.

When version or rendering context is unclear, identify the uncertainty instead
of assuming a different Nuxt model.

## Technical checks

### 1. Nuxt integration contracts

Check that:

- file-based routes and dynamic parameters produce the intended URLs;
- pages, layouts, middleware, components, composables, plugins, and server
  handlers use names that match Nuxt registration rules;
- `app.vue`, layouts, and nested pages render `<NuxtPage>` or `<slot />` where
  required;
- runtime configuration keys, plugin injections, aliases, payloads, and endpoint
  contracts remain consistent;
- new dependencies and modules are present in the appropriate package section
  and lockfile;
- generated files such as `.nuxt/` and `.output/` are not edited or committed as
  source;
- framework integration is not bypassed in a way that breaks routing, payload
  transfer, generated types, SSR, or deployment.

### 2. Configuration and directory structure

Check that:

- `nuxt.config.*` uses options supported by the installed version;
- values serialised by Nuxt or Nitro are serialisable;
- clients, functions, class instances, `Map`, `Set`, and other runtime objects
  are created in runtime code rather than serialised configuration;
- `app.config.*` contains public application configuration, not secrets;
- private values remain outside `runtimeConfig.public`;
- `shared/` contains environment-neutral types and utilities;
- `shared/` does not import Nuxt app context, Nitro request context, Vue
  reactivity, browser-only code, or Node-only code;
- `#server` imports remain in server contexts;
- `public/` is used for assets that require stable root URLs;
- build-processed assets are imported from the configured assets directory;
- custom directories, aliases, layers, and module order preserve the intended
  override behaviour.

Watch for:

- nested plugin or component directories that are not scanned by the installed
  Nuxt version;
- server-only dependencies entering application or shared bundles;
- `~/assets/...` being used as a public runtime URL;
- secrets exposed through public environment variables, `vite.define`, client
  plugins, or application configuration.

### 3. Vue components, composables, and reactivity

Check that:

- props, emits, slots, and model contracts are coherent;
- props are not mutated directly;
- reactive values are not destructured in a way that loses reactivity under the
  active Vue compiler behaviour;
- watchers do not create loops, duplicate requests, or repeated side effects;
- subscriptions, observers, listeners, and third-party widgets are cleaned up;
- DOM APIs and browser-only packages are initialised in client-safe lifecycle
  boundaries;
- composables that require Nuxt context run inside a valid Nuxt context;
- async custom composables do not call contextual composables after an arbitrary
  `await` when that loses the Nuxt instance;
- component and composable names do not collide with Nuxt compiler-reserved or
  auto-imported names;
- request-specific or user-specific state is not stored in module-level mutable
  singletons.

Prefer plain utilities for logic that does not require Vue reactivity or Nuxt
context.

Use `.client`, `.server`, `<ClientOnly>`, lazy components, islands, or server
components only when supported by the installed version and justified by the
rendering requirements.

### 4. Pages, layouts, routing, and middleware

Check that:

- route filenames and parameter names match the installed Nuxt conventions;
- parent pages render child routes where nested routing requires it;
- layouts provide the required content slot and valid root structure;
- `definePageMeta` is used in page context;
- referenced layouts and middleware exist under their registered names;
- middleware names account for Nuxt kebab-case normalisation;
- route middleware uses the supplied `to` and `from` values;
- redirects and aborted navigations are returned or awaited;
- redirect rules cannot loop;
- navigation preserves required params, query values, hashes, locale, and state;
- internal navigation uses Nuxt routing rather than unnecessary full-page
  reloads;
- static files and external applications are not incorrectly routed through the
  client router;
- Nuxt's `useRoute()` behaviour is not accidentally replaced by an incompatible
  import from `vue-router`.

Route middleware is not an authorisation boundary. Protected data and mutations
must be authorised in Nitro, an upstream API, or another trusted server
boundary.

### 5. SSR, hydration, and client-only behaviour

For universal or hybrid rendering, check that:

- server-evaluated code does not access `window`, `document`, `navigator`,
  storage APIs, DOM constructors, or browser-only globals;
- server and client produce compatible initial markup and reactive state;
- initial values do not diverge because of uncontrolled time, randomness,
  timezone, locale, browser dimensions, or client storage;
- request-specific state is isolated between server requests;
- SSR state and async data are transferred through the Nuxt payload;
- client-only side effects run after mount or inside a client-specific boundary;
- browser-only packages with top-level side effects do not enter the server
  bundle;
- sensitive server values are not serialised into HTML, page props, application
  state, or the Nuxt payload;
- hydration warnings are not suppressed when they represent a real content,
  state, or interaction mismatch.

Whole-route SSR disablement should not be used only to hide an SSR defect.

### 6. Data fetching and async data

Use the primitive that matches the execution model:

- `useFetch` for SSR-aware HTTP data required during setup or initial rendering;
- `useAsyncData` for SSR-aware arbitrary async logic;
- `$fetch` for interactions, mutations, client-only actions, and explicit
  requests.

Check that:

- initial universal-rendered data is not fetched unnecessarily on both server
  and client;
- async-data keys are stable and identify the resource, parameters, user,
  tenant, and locale where relevant;
- custom wrappers provide deterministic keys;
- calls sharing a key use compatible handlers, defaults, transforms, picks,
  cache functions, and deep or shallow behaviour;
- successful handlers return defined values;
- async-data handlers do not perform mutations, analytics, notifications, or
  other repeatable side effects;
- reactive URLs, params, bodies, headers, and watch sources do not cause request
  storms;
- lazy, disabled, or client-only requests handle idle, pending, missing data,
  errors, and explicit execution;
- obsolete requests use deduplication or abort signals where supported;
- mutation requests prevent harmful duplicate submission;
- fetch failures are not silently converted into misleading empty success
  states;
- sensitive upstream response fields are not transferred into the client
  payload.

For request-bound server calls, check that:

- required cookies and headers are forwarded intentionally;
- unsafe incoming headers are not blindly proxied;
- credentials are not forwarded to an origin derived from untrusted input;
- internal request context is propagated only when required.

At API boundaries, convert dates, big integers, maps, sets, errors, classes, and
custom domain objects into deliberate serialised representations.

### 7. State, cookies, and runtime configuration

#### State

Check that:

- shared SSR state is request-safe;
- `useState` keys do not collide;
- payload state contains serialisable values;
- service clients, functions, DOM nodes, and unsupported class instances are not
  stored in payload state;
- user, tenant, locale, permission, and request-specific values are not stored in
  process-global state;
- logout, account switching, tenant switching, and permission changes clear or
  recompute sensitive state;
- Pinia or another store is integrated through a Nuxt-compatible,
  request-isolated mechanism.

#### Cookies

Check that:

- app code uses an SSR-aware cookie mechanism;
- server code uses request-aware H3 cookie utilities;
- authentication cookies are not client-readable unless required by the
  architecture;
- security-sensitive cookies use suitable `Secure`, `HttpOnly`, `SameSite`,
  path, domain, expiry, and prefix settings;
- large application objects are not stored directly in cookies;
- server cookie changes do not leave stale client state.

#### Runtime configuration

Check that:

- private values remain in private runtime config and trusted server code;
- runtime values use matching `NUXT_...` environment-variable names;
- production does not depend on development `.env` loading;
- runtime config contains data, not clients, functions, or mutable service
  instances;
- private configuration is not logged, returned by APIs, copied into payload
  state, embedded in errors, or forwarded to the browser;
- durable server state is not assumed to survive in process memory across
  instances or restarts.

### 8. Nitro handlers and H3 boundaries

Check that:

- handlers export a valid `defineEventHandler`, `eventHandler`, or established
  project wrapper;
- mutation endpoints constrain HTTP methods;
- params, query values, headers, cookies, and bodies receive runtime validation;
- authentication and authorisation run on the server;
- ownership, tenant, role, and field-level permissions are enforced independently
  of client input;
- invalid input produces an appropriate 4xx response;
- unexpected errors do not expose stacks, credentials, SQL, file paths, or
  upstream internals;
- handlers return deliberate bodies and status codes;
- server middleware does not accidentally terminate or replace route handling;
- route middleware and server middleware are not confused;
- external URLs, redirects, proxy targets, file paths, and fetch destinations are
  constrained against SSRF, open redirects, traversal, and credential leakage;
- cookie-authenticated mutations address CSRF under the application's origin and
  `SameSite` model;
- user-controlled values use context-appropriate APIs for HTML, SQL, shell,
  templates, headers, and logs;
- destructive multi-step work uses transactions or a compensation strategy where
  required.

Use `event.$fetch` when an internal downstream call needs the current request
context. Use ordinary `$fetch` when request forwarding is not desired.

### 9. Error handling and lifecycle resilience

Check that:

- missing resources produce the intended 404 behaviour and status;
- server failures are not returned as successful empty responses;
- loading and failure paths do not leave endless spinners, disabled controls,
  stale success messages, or duplicate submissions;
- error handling does not leak secrets or sensitive request data;
- global and local error boundaries provide viable recovery;
- clearing an error cannot create a redirect loop;
- recoverable failures preserve user-entered form data where practical;
- cleanup logic remains correct across Nuxt transitions and Suspense lifecycle
  ordering;
- retries and refreshes are bounded.

### 10. Head management and public rendering

For public or indexable routes, check that:

- the rendering mode exposes required primary content and metadata;
- title and description data match the rendered route;
- canonical, robots, social, alternate-language, and structured-data values
  match the canonical content;
- dynamic metadata handles missing data and route errors;
- user-controlled values do not enter unsafe HTML, head fields, or raw scripts;
- navigation does not leave stale metadata from the previous route;
- private, authenticated, staging, error, duplicate, and thin routes are not
  unintentionally indexable.

Use:

- `useSeoMeta` for typed SEO metadata;
- `useHead` for broader reactive head management;
- `useHeadSafe` for untrusted or user-generated values;
- static application head configuration for global non-reactive tags;
- `definePageMeta` only for route metadata, not document head metadata.

### 11. Payload, assets, and client bundle

Check that:

- independent data requests do not form avoidable serial waterfalls;
- unused response fields and large state objects are not unnecessarily placed in
  the Nuxt payload;
- heavy browser-only dependencies do not enter every route or the server bundle;
- route-level splitting is not defeated by eager imports or blanket global
  registration;
- images and media reserve layout space;
- likely LCP media is not delayed through inappropriate lazy loading;
- client-only fallbacks do not create avoidable layout shift or hide essential
  content;
- plugins, watchers, polling, hooks, and listeners do not multiply across
  navigation;
- global plugins do not block startup with unrelated work;
- performance-oriented caching does not expose stale or private data.

Use Nuxt Image components only when the module is installed and configured.

### 12. Rendering modes, route rules, caching, and deployment

Universal rendering, SPA rendering, prerendering, SWR, ISR, and edge rendering
are different architectural modes. Their suitability depends on product and
deployment requirements.

Check that:

- rendering choices match SEO, authentication, freshness, interactivity, cost,
  and hosting requirements;
- route-rule globs target only the intended routes;
- redirects preserve status, params, query values, and destination intent;
- CORS trusts only the required origins, methods, and headers;
- cached output is invariant for every request sharing the cache key;
- authenticated, personalised, tenant-specific, locale-specific, experimental,
  permission-dependent, cookie-dependent, or header-dependent content is not
  cached as one public response;
- mutation endpoints, one-time tokens, realtime responses, and sensitive data are
  not cached;
- invalidation and freshness match the data lifecycle;
- prerendered routes have access to required build-time data and secrets;
- dynamic static routes are discoverable or explicitly enumerated;
- static hosting does not depend on unavailable Nitro endpoints or server
  sessions;
- SPA fallback and real 404 behaviour match hosting rewrites;
- the Nitro preset matches the actual runtime;
- production environment variables use names recognised by Nuxt and Nitro;
- Node APIs, filesystem writes, native binaries, long-lived connections,
  background work, and process-local state are compatible with the target
  runtime.

Treat in-memory storage as instance-local unless shared storage is configured.

### 13. Plugins, modules, layers, and auto-imports

#### Plugins

Check that:

- plugins are located in scanned directories or explicitly registered;
- browser-only and server-only plugins use the correct execution boundary;
- plugin injections are typed in TypeScript projects;
- dependencies between plugins use a stable ordering mechanism;
- parallel plugins do not depend on each other's completion;
- plugin composables do not depend on later plugins;
- setup remains idempotent under HMR, tests, islands, or multiple app instances;
- plugins are not both auto-registered and explicitly registered.

#### Modules and layers

Check that:

- modules support the installed Nuxt version and rendering target;
- configuration keys match the installed module version;
- module and layer order preserves intended overrides;
- local modules use Nuxt Kit rather than directly editing generated files;
- layer-relative aliases, paths, components, composables, and configuration merge
  correctly;
- published layers and modules declare their own runtime dependencies.

#### Auto-imports

Check that:

- symbols are auto-imported in the relevant app, server, or shared context;
- name collisions do not bind to the wrong function;
- explicit imports do not select incompatible functions with the same name;
- components outside default directories are configured for scanning or imported
  explicitly.

### 14. TypeScript and generated types

Check that:

- Vue and TypeScript changes match the project strictness;
- app, server, shared, config, and layer code use the correct type environments;
- type augmentations are visible to the relevant Nuxt project references;
- API request and response types match runtime validation and serialised values;
- aliases, modules, components, composables, plugin injections, and runtime config
  keys appear in generated or augmented types;
- `tsconfig.json` preserves Nuxt-generated aliases, auto-imports, server types, and
  project references;
- generated declarations are not edited manually;
- runtime input is not trusted only because a TypeScript type exists;
- broad `any`, unchecked assertions, non-null assertions, and `@ts-ignore` do not
  conceal framework-contract errors.

`nuxt dev` and `nuxt build` do not necessarily perform a full type check. Type
correctness requires evidence from the project's configured type-check workflow.

### 15. Testing

Where the repository has an established test layer, check that:

- affected route, component, composable, plugin, API, and configuration tests are
  updated;
- protected server logic covers unauthenticated, forbidden, invalid, ownership,
  and cross-tenant cases;
- data-fetching tests cover changed loading, success, error, refetch, and reactive
  key behaviour;
- SSR-sensitive changes verify server rendering and hydration;
- deployment-mode changes are tested against a built or preview environment;
- pure utilities use plain unit tests;
- Nuxt-context code uses the Nuxt test environment;
- navigation, redirects, cookies, authentication, hydration, and direct URL entry
  use browser or integration tests where appropriate;
- tests assert application behaviour and server contracts rather than only
  framework implementation details;
- shared global state does not make tests order-dependent.

### 16. Version migration and compatibility

Check that:

- migration code matches the actual source and target Nuxt versions;
- Nuxt 2 conventions are not introduced into Nuxt 3 or Nuxt 4 without an explicit
  compatibility mechanism;
- Nuxt 3-to-4 structure changes account for source directories, aliases, CSS,
  tests, layers, and deployment configuration;
- Unhead, Vue, Vite, Nitro, H3, and module APIs are evaluated against installed
  versions;
- compatibility flags are considered when they alter routing, component naming,
  async data, TypeScript, Vite environments, or plugin behaviour;
- experimental and future-compatibility flags are not used as isolated fixes
  without evaluating their project-wide effects;
- framework upgrades remain separate from unrelated product changes where
  practical.

## High-risk Nuxt patterns

Pay particular attention to:

- private runtime values exposed through public config, payload state, browser
  storage, HTML, or API responses;
- module-level reactive state containing per-user or per-request data;
- authorisation implemented only in route middleware or hidden UI;
- public caching of authenticated, tenant-specific, or personalised output;
- browser-only code executing during SSR;
- server and client initial output producing incompatible hydration;
- bare `$fetch` for initial universal-rendered setup data when it repeats work or
  side effects during hydration;
- mutations or side effects inside `useAsyncData`;
- static deployment that depends on Nitro APIs or server sessions;
- edge deployment using unsupported Node APIs or native dependencies;
- unvalidated server input enabling injection, SSRF, traversal, cross-tenant
  access, or destructive invalid mutations;
- `navigateTo` or `abortNavigation` calls that are neither returned nor awaited;
- request credentials forwarded to untrusted or user-controlled origins;
- ISR or SWR applied to private routes without a correct variation strategy.

## Common false positives

Do not treat these as Nuxt defects without concrete impact:

- a Nuxt 3 project not using the Nuxt 4 `app/` directory;
- explicit imports instead of auto-imports;
- the Options API;
- `ssr: false` in a private application;
- absence of Nuxt Image when the module is not installed;
- a small response not using `pick` or `transform`;
- absence of layers, islands, server components, or experimental features;
- type checking occurring in a separate workflow rather than during
  `nuxt build`;
- a supported deprecation that the change does not worsen.

## References

This skill is based primarily on the official documentation for Nuxt, Nitro, H3,
Vue, and Unhead.

- https://nuxt.com/docs/
- https://nitro.build/docs/
- https://h3.dev/
- https://vuejs.org/guide/scaling-up/ssr.html
- https://unhead.unjs.io/

Installed versions and repository configuration take precedence over examples
from any single documentation version.

---
id: web_development
name: Web Development
category: web_review
description: >
  Provides platform-agnostic web development review knowledge for functional
  correctness, HTML foundations, accessibility, security, privacy, SEO,
  performance, resilience, internationalisation, and machine readability.
phase: code_review
artifacts:
    - git_diff
    - changed_files
output: json
---

# Web Development

## Scope

This skill covers platform-agnostic correctness and quality for web
applications and websites.

It applies to changes involving:

- HTML documents and semantic structure;
- navigation, controls, forms, media, and tables;
- public routes, metadata, indexing, and discoverability;
- accessibility and keyboard interaction;
- client-side and server-side security boundaries;
- personal data, consent, storage, and third-party services;
- loading performance, rendering stability, and asset delivery;
- error handling, failure recovery, and progressive enhancement;
- localisation, language, direction, and locale-sensitive formatting;
- machine-readable content, structured data, and agent discovery.

Use repository configuration, product requirements, browser support targets,
deployment architecture, and established project conventions as the source of
truth.

Apply only the sections relevant to the changed surface. Do not require
specialised capabilities such as offline support, identity discovery,
internationalisation, or agent protocols unless the product or task uses them.

## Technical checks

### 1. Functional correctness and integration

Check that:

- the requested behaviour and acceptance criteria are implemented;
- imports, exports, routes, selectors, events, component contracts, API payloads,
  and configuration names remain consistent;
- loading, empty, success, validation, unauthenticated, forbidden, not-found, and
  failure states are handled where relevant;
- user actions use the correct semantic control and trigger the intended action;
- state transitions do not introduce duplicate requests, races, stale state,
  destructive retries, data corruption, hydration mismatches, or unbounded work;
- mocks, placeholders, debug code, temporary bypasses, secrets, credentials, and
  machine-specific values are not committed accidentally;
- changed contracts are reflected in the repository's existing tests and
  verification mechanisms.

### 2. HTML foundations and semantics

#### Documents

Check that standalone HTML documents:

- use the HTML doctype;
- declare UTF-8 early;
- set a valid language on the root `html` element;
- include a mobile viewport that does not disable zoom;
- contain exactly one meaningful, non-empty document title;
- expose one primary `main` landmark;
- use coherent landmark and heading structure.

#### Elements

Check that:

- anchors navigate;
- buttons perform actions;
- headings represent section hierarchy;
- lists represent actual collections;
- tables represent tabular data;
- form controls use the correct native element and input type;
- interactive elements are not nested illegally;
- IDs are unique;
- labels, descriptions, headings, and relationships use valid references;
- published URLs remain stable unless the change includes a migration.

Prefer native HTML primitives such as `button`, `a`, `details`, `summary`,
`dialog`, forms, popovers, and declarative controls when they meet the
requirements and browser support policy.

Avoid:

- clickable generic elements when a native control fits;
- manual line breaks used only to force responsive wrapping;
- custom focus, positioning, or disclosure logic when a reliable native
  primitive already provides the required behaviour;
- heading levels chosen only for visual appearance.

### 3. Public metadata and discoverability

Apply this section to public, indexable routes.

Check that:

- each indexable page has a meaningful title;
- descriptions and canonical URLs reflect the actual page where used;
- Open Graph and social metadata are coherent for shareable content;
- metadata does not remain stale after client-side navigation;
- redirects use a status that matches their permanence;
- redirect chains and redirect loops are not introduced;
- missing content returns a real 404 rather than a soft 404;
- public, private, staging, duplicate, error, and thin content have deliberate
  indexing policies;
- primary public content and metadata are available in crawlable output when
  client-only rendering would prevent discovery;
- changed public URLs receive appropriate redirects;
- internal links use crawlable anchors and useful link text;
- structured data is valid, relevant, and consistent with visible content;
- breadcrumbs match the actual hierarchy;
- canonical URLs and sitemap entries identify the same preferred URLs.

Where applicable, check that:

- `robots.txt` reflects the intended crawl policy;
- sitemaps contain canonical, indexable URLs;
- large sitemap sets use sitemap indexes;
- URLs are descriptive, stable, consistently cased, and consistently separated;
- favicons, application icons, theme metadata, and colour-scheme metadata match
  the product;
- feeds expose stable item identifiers and are discoverable.

Avoid:

- soft 404s;
- conflicting canonicals;
- duplicated titles or descriptions;
- public content that depends on fragile client-side execution;
- structured data that describes content not visible to users;
- blanket crawler blocking that conflicts with intended public access.

### 4. Accessibility

#### Structure and names

Check that:

- semantic HTML and landmarks expose the page structure;
- heading levels form a coherent outline;
- every interactive control has an accessible name;
- icon-only controls have an explicit accessible name;
- links describe their destination or purpose;
- informative images have useful alternative text;
- decorative images use empty alternative text;
- form controls have programmatically associated labels;
- groups of controls have appropriate group labels;
- inline and document language changes are marked correctly.

#### Keyboard and focus

Check that:

- all interactions work with a keyboard;
- keyboard order follows the visual and logical order;
- focus remains visible in all supported states;
- focus is moved intentionally when dialogs, menus, route changes, or dynamic
  workflows require it;
- blocking modals trap focus appropriately and make background content inert;
- closing a transient surface restores focus to a sensible location;
- repeated navigation can be bypassed with a working skip link where applicable;
- no interaction creates a keyboard trap.

Avoid positive `tabindex` as a repair for incorrect DOM order.

#### Forms and validation

Check that:

- validation errors are textual;
- errors are associated with their controls;
- dynamically introduced errors are announced when required;
- instructions do not depend only on colour, position, shape, or sound;
- required fields are identified programmatically;
- authentication supports password managers and paste;
- mobile inputs use suitable `type`, `autocomplete`, `inputmode`, and
  `enterkeyhint`;
- previously supplied information is not requested again unnecessarily;
- recoverable failures preserve entered data where practical.

#### Visual presentation and motion

Check that:

- text and meaningful interface elements have sufficient contrast;
- focus, hover, active, disabled, selected, invalid, and success states remain
  distinguishable;
- information is not conveyed by colour alone;
- zoom and text resizing do not break essential content or controls;
- reflow does not require two-dimensional scrolling except for inherently
  two-dimensional content;
- motion respects `prefers-reduced-motion`;
- forced-colours mode preserves meaning and operation;
- pointer targets meet the applicable WCAG target-size requirement or provide
  sufficient spacing.

#### Media and data

Check that:

- prerecorded media includes required captions, transcripts, or audio
  descriptions;
- autoplay and sound behaviour remain controllable;
- data tables use real table markup;
- tables have an accessible name where needed;
- header cells and data cells have correct relationships;
- complex visualisations expose an equivalent textual or tabular representation
  where required.

Avoid:

- accessibility overlays as a substitute for accessible implementation;
- placeholder-only labels;
- removed focus outlines without replacement;
- empty controls;
- contradictory ARIA roles or states;
- ARIA used where native semantics already provide the required behaviour.

### 5. Security

Apply infrastructure checks only when the relevant server, hosting, proxy,
middleware, or deployment configuration is visible.

#### Transport and browser protections

Check that:

- production traffic uses HTTPS;
- mixed active content is not introduced;
- HSTS is enabled only after HTTPS is valid for the intended hosts;
- responses prevent MIME sniffing;
- untrusted framing is prevented;
- referrer policy limits unnecessary cross-origin URL leakage;
- permissions policy disables unused powerful capabilities;
- cross-origin isolation is enabled only when compatible with required
  integrations.

#### Input and output handling

Check that untrusted values are handled correctly for their destination:

- HTML and DOM;
- JavaScript;
- CSS;
- URLs and redirects;
- SQL and database filters;
- templates;
- shell commands;
- filenames and filesystem paths;
- headers and logs.

Avoid unsafe DOM injection with untrusted strings.

Check that:

- external navigation validates untrusted destinations;
- redirects cannot become open redirects;
- uploads validate type, size, filename, and storage destination;
- downloads cannot expose arbitrary files;
- dynamically fetched URLs cannot produce SSRF;
- path input cannot escape an intended directory;
- error messages do not disclose stack traces, credentials, infrastructure, SQL,
  or internal paths.

#### Authentication, authorisation, and secrets

Check that:

- authentication and authorisation are enforced at a trusted boundary;
- client-side visibility is not treated as access control;
- ownership, tenant, role, and field-level permissions are enforced independently
  of client input;
- secrets and privileged credentials are not committed;
- secrets are not shipped to the browser;
- public runtime configuration does not contain long-lived credentials;
- logout clears sensitive local state where required;
- session changes invalidate stale privileged state.

#### Cookies and sessions

Check that security-sensitive cookies use suitable:

- `Secure`;
- `HttpOnly` when JavaScript access is unnecessary;
- explicit `SameSite`;
- path and domain scope;
- expiry;
- secure cookie prefixes where appropriate.

Cookie-authenticated mutations must address CSRF according to the application's
origin and `SameSite` model.

#### Content Security Policy

Where a CSP exists or is introduced, check that:

- script, style, image, frame, font, media, worker, and connection sources are
  constrained deliberately;
- framing policy matches product requirements;
- nonces or hashes are used correctly;
- broad wildcards do not defeat the policy;
- `unsafe-eval` and `unsafe-inline` are not added without a demonstrated
  requirement;
- violation reports do not expose sensitive infrastructure data.

Where applicable, consider:

- Subresource Integrity for mutable third-party assets;
- Trusted Types for material DOM injection surfaces;
- `/.well-known/security.txt` for vulnerability disclosure.

### 6. Privacy and consent

Apply this section when the feature collects, stores, processes, transmits, or
reveals personal data.

Check that:

- collected fields have a defined product purpose;
- the feature collects only the data it needs;
- privacy disclosures match the actual collection, purpose, legal basis,
  sharing, retention, and user rights;
- personal or sensitive data does not leak through URLs, logs, analytics,
  bundles, errors, caches, or public storage;
- third-party transmission is justified and minimised;
- retention and deletion behaviour match the stated policy;
- analytics identifiers and events do not contain unnecessary personal data.

When opt-in consent is required, check that:

- non-essential cookies and storage wait for valid consent;
- scripts, tags, embeds, and SDKs remain inactive before consent;
- rejecting consent is not materially harder than accepting it;
- consent state persists and is respected across navigation;
- withdrawing consent stops later processing where required;
- third-party embeds do not bypass the consent state.

Where legally and technically applicable, honour Global Privacy Control or other
recognised preference signals.

Avoid:

- pre-consent tracking where consent is required;
- consent dark patterns;
- sensitive data in public URLs;
- collecting fields without a defined purpose;
- transmitting complete user records when aggregate or reduced data is
  sufficient.

### 7. Performance and delivery

A static code review can identify credible risks but cannot establish measured
Core Web Vitals.

#### Rendering and layout

Check that:

- images and media reserve layout space;
- likely LCP content is not lazy-loaded;
- content insertion does not create avoidable layout shift;
- fonts and interface state changes do not produce unstable geometry;
- mobile full-height layouts use appropriate viewport units;
- scrollbar changes do not shift the layout unnecessarily;
- large off-screen sections use containment or visibility primitives only when
  beneficial and compatible.

#### Assets

Check that:

- images use suitable dimensions and efficient formats;
- responsive images provide appropriate candidates where needed;
- off-screen media is lazy-loaded;
- fonts use efficient formats and appropriate subsetting;
- `font-display` matches the product's rendering requirements;
- font, script, style, image, and connection preloads are selective;
- fingerprinted assets use long immutable caching;
- HTML and personalised responses use appropriate cache and revalidation rules;
- text assets are compressed by the delivery layer.

#### JavaScript and CSS

Check that:

- scripts use `module`, `defer`, or `async` according to dependency and execution
  order;
- synchronous third-party scripts do not block initial rendering unnecessarily;
- global bundles do not absorb large feature-specific dependencies;
- unused code and styles are not shipped across unrelated routes;
- event listeners, observers, timers, and polling are bounded and cleaned up;
- expensive input, scroll, resize, and pointer work does not overload the main
  thread;
- CSS or observation APIs replace continuous event handling where suitable;
- critical CSS is not delayed behind unnecessary requests;
- render-blocking resources are reduced without breaking order or behaviour.

#### Data and network

Check that:

- independent requests do not form avoidable waterfalls;
- duplicate requests are not introduced;
- large responses do not include unused fields;
- cacheable responses support validators or conditional requests where useful;
- retries are bounded;
- destructive requests are not retried without idempotency protection;
- speculative prefetching does not fetch private, expensive, or unlikely
  resources;
- back-forward cache eligibility is not broken without need.

Avoid:

- lazy-loading the LCP element;
- blanket preload or prefetch;
- domain sharding retained for obsolete HTTP/1.1 constraints;
- image sprites retained only to reduce request count;
- unsupported claims that performance improved without measurement evidence.

### 8. Resilience and failure recovery

Check that:

- error pages return the correct status;
- failures are explained in plain language;
- internal details are not exposed;
- error surfaces provide a useful next step;
- network, API, and validation failures do not leave the UI stuck or misleading;
- partial failure does not corrupt valid state;
- repeated submission does not duplicate non-idempotent actions;
- user-entered data is preserved where practical;
- retries are bounded and appropriate to the operation;
- offline or intermittent connectivity does not silently report success;
- loading indicators correspond to real pending work;
- cancellation and stale responses do not overwrite newer state;
- non-essential JavaScript failure does not unnecessarily destroy core content
  or primary navigation.

Where applicable, check that:

- planned downtime returns `503`;
- retry guidance is meaningful;
- service workers have an intentional cache policy;
- authenticated and fast-changing data is not cached indiscriminately;
- service-worker updates cannot strand users on incompatible asset versions;
- installable applications provide a valid manifest;
- products promising offline use provide a deliberate offline fallback;
- production-critical services have external monitoring and a separately hosted
  status surface.

Avoid:

- returning `200` for error content;
- raw stack traces;
- infinite retry loops;
- fire-and-forget destructive actions without confirmation or idempotency;
- service-worker caching rules that expose user-specific responses.

### 9. Internationalisation

Apply this section when the product supports multiple languages, locales,
regions, writing directions, or formatting conventions.

Check that:

- document language matches rendered content;
- inline language changes are marked;
- text direction matches the language and content;
- strings are not concatenated in ways that prevent translation or reordering;
- dates, numbers, currencies, units, lists, and plural forms use locale-aware
  formatting;
- singular and plural logic does not assume English grammar;
- non-translatable brands, code, and identifiers remain stable;
- translated content includes translated metadata and alternative text;
- CSS uses logical properties where physical directions would break RTL or
  alternative writing modes;
- locale switching is explicit and preserves the equivalent destination;
- language names are displayed in their own language;
- flags are not used as language identifiers.

For multilingual public sites, check that:

- one consistent URL strategy is used;
- locale URLs are canonicalised deliberately;
- `hreflang` alternates are valid, reciprocal, canonical, and correctly coded;
- automatic locale detection does not trap users or crawlers;
- IP-based redirects do not prevent access to another locale.

### 10. Well-known resources and protocol discovery

These checks apply only when the product uses the corresponding protocol or
capability.

Check that:

- standard metadata uses registered `/.well-known/` locations;
- account-based sites expose a change-password redirect where required;
- identity providers publish valid discovery metadata;
- Apple and Android association files contain the exact intended apps, domains,
  paths, and signing identities;
- federated products expose the discovery resources required by their protocol;
- machine-readable API catalogues accurately describe available services;
- related-origin WebAuthn, NodeInfo, traffic advice, and similar resources match
  their protocol requirements.

Do not require unrelated well-known resources for an ordinary website.

### 11. Machine readability and agent discovery

Apply this section to public information, documentation, catalogues, APIs, or
products intended for machine and agent discovery.

Check that:

- public URLs are stable;
- crawler policy matches intended public and private access;
- semantic HTML exposes meaningful entities and relationships;
- structured data matches visible content;
- important content has suitable machine-readable alternatives such as JSON,
  RSS, Atom, or Markdown where useful;
- machine-readable representations are discoverable from canonical pages;
- HTTP `Link` headers advertise feeds, sitemaps, alternate representations, or
  tool endpoints where useful;
- `/llms.txt` or an equivalent curated index points to authoritative content when
  the product uses it;
- AI crawler policy is explicit when differentiated access is intended;
- skill, API, or tool metadata describes real callable capabilities;
- discovery metadata does not expose private endpoints or credentials.

Emerging mechanisms such as MCP, A2A, WebMCP, agent cards, conversational
endpoints, bot authentication, and DNS-based discovery are contextual rather
than universal requirements.

### 12. Progressive enhancement and browser compatibility

Check that:

- essential content remains available when non-essential JavaScript fails;
- native navigation and form submission are preserved where the architecture
  allows;
- browser-only APIs are feature-detected where support is not guaranteed;
- required polyfills match the browser support policy;
- new CSS and HTML features have acceptable fallbacks;
- unsupported features fail without making core workflows inaccessible;
- JavaScript does not prevent default browser behaviour without providing a
  complete replacement;
- deep links, refreshes, history navigation, and direct URL entry work in the
  deployed routing model;
- custom elements and enhanced controls expose a usable pre-upgrade state where
  relevant.

Avoid:

- replacing resilient browser behaviour with JavaScript without product benefit;
- relying on experimental features outside the declared support policy;
- hiding core content until hydration when server or static content is
  available.

## High-risk web patterns

Pay particular attention to:

- actions implemented with inaccessible generic elements;
- controls without accessible names;
- inaccessible primary workflows;
- client-side-only authorisation;
- secrets or personal data exposed in browser bundles, logs, URLs, or public
  configuration;
- untrusted values reaching HTML, DOM, script, URL, SQL, shell, filesystem, or
  redirect contexts unsafely;
- consent interfaces that load trackers before consent;
- soft 404s and accidental deindexing of public content;
- indexing of private or authenticated content;
- client-only rendering that hides required public content from crawlers;
- lazy-loaded LCP content;
- layout shifts caused by images, fonts, or dynamic insertion;
- retries that duplicate destructive actions;
- service workers caching authenticated responses;
- localisation implemented through string concatenation or hard-coded locale
  formatting;
- state changes that leave stale permissions, personal data, or consent choices
  active.

## Common false positives

Do not treat these as defects without concrete product requirements or evidence:

- absence of Open Graph metadata on private pages;
- absence of a sitemap on a small non-indexable application;
- absence of PWA or offline support;
- absence of `/.well-known/` files unrelated to the product;
- absence of `/llms.txt` or emerging agent protocols;
- use of client-side rendering for a private application;
- absence of structured data where no supported vocabulary fits;
- absence of Subresource Integrity for immutable self-hosted assets;
- absence of multilingual handling in a single-locale product;
- use of a custom control when a native control cannot satisfy the interaction
  and accessibility requirements;
- lack of performance claims or Core Web Vitals evidence in a static diff.

## Attribution

Adapted, condensed, paraphrased, and reorganised from **The Website
Specification** checklist by Joost de Valk and contributors.

- Source: https://specification.website/checklist/
- Project: https://github.com/jdevalk/specification.website
- Source content licence: CC BY 4.0
- Changes: reorganised the checklist as platform-agnostic technical knowledge for
  automated review; removed reviewer persona, process, strictness, scoring, and
  output instructions.

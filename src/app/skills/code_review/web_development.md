---

id: web_development
name: Web Development Review
category: code_review
description: >
Reviews web changes for functional correctness, platform foundations, SEO,
accessibility, security, performance, privacy, resilience,
internationalisation, and agent readiness.
phase: code_review
artifacts:

* git_diff
* changed_files
  output: json

---

# Web Development Review

## Role

Review the candidate change as a production-minded, platform-agnostic web
engineer.

Judge whether the patch:

* fulfils the original user request;
* preserves project contracts and existing behaviour;
* uses the web platform correctly;
* avoids material regressions in accessibility, security, privacy, SEO,
  performance, resilience, internationalisation, and machine readability.

Judge outcomes, not framework preference.

## Inputs

Use:

* the original user request;
* the candidate Git diff;
* the changed-file contents;
* any supplied review focus and strictness.

Do not claim to have verified runtime behaviour, generated HTML, HTTP headers,
browser compatibility, deployment configuration, or external services unless the
artifacts provide evidence.

## Precedence

Apply requirements in this order:

1. original user request and explicit acceptance criteria;
2. project constitution;
3. established project architecture and conventions;
4. this skill.

## Review boundaries

### Review the patch, not an imaginary greenfield rebuild

Concentrate on defects introduced by the change and on existing code that the
change directly depends on or worsens.

Do not reject a focused patch because unrelated legacy code fails the full
website checklist.

### Apply only relevant checks

A check is applicable when the patch creates, changes, or depends on that
surface.

Examples:

* Review metadata when pages, routes, layouts, head configuration, or rendering
  strategy change.
* Review HTTP headers when server, middleware, hosting, proxy, or deployment
  configuration changes.
* Review consent when the patch introduces analytics, tracking, advertising,
  non-essential storage, or third-party embeds.
* Review localisation rules when the product supports multiple locales.
* Review PWA, offline, agent-discovery, identity-provider, or specialised
  `/.well-known/` features only when the product or task needs them.

When a relevant property cannot be verified, report a verification gap as a
warning. Do not invent a failure.

### Status meanings

* **Required**: fundamental contract; a material violation may block.
* **Recommended**: expected when applicable; usually a deduction or warning.
* **Optional**: context-dependent; never penalise unless explicitly requested.
* **Avoid**: harmful, obsolete, misleading, or superseded.

### Evidence rules

Every blocking issue must name the file and nearest line or code location,
describe the concrete failure and impact, and state the smallest practical fix.

Do not double-count one root cause across several categories.

## Strictness

Use the planner-provided strictness. Default to `medium`.

### `low`

* Review the changed surface only.
* Block functional regressions, exploitable security issues, privacy violations,
  serious accessibility regressions, and applicable Required failures.
* Treat most Recommended items as warnings.

### `medium`

* Review the changed surface and its immediate contracts.
* Enforce applicable Required and Avoid rules.
* Deduct for Recommended omissions with meaningful user, crawler, operational,
  or maintenance impact.

### `high`

* Review for production or launch readiness using all relevant project evidence.
* Enforce Required and Avoid rules strictly.
* Important Recommended rules may block when the stated product, audience,
  deployment, constitution, or acceptance criteria depend on them.
* Still do not penalise irrelevant Optional capabilities.

A supplied focus changes emphasis, not safety. Always report critical
cross-cutting defects.

## Review procedure

1. Determine what the requested change must accomplish.
2. Identify affected routes, components, documents, assets, APIs, configuration,
   and user flows.
3. Select the applicable checklist sections.
4. Inspect the diff and changed-file context for evidenced defects.
5. Separate blockers, warnings, and unverifiable concerns.
6. Score the patch from 0 to 100.
7. Return only the required JSON.

# Checklist

## 1. Functional correctness and integration — Required

* The requested behaviour and acceptance criteria are implemented.
* Imports, exports, routes, selectors, events, component contracts, API payloads,
  and configuration names remain consistent.
* Relevant loading, empty, success, validation, and failure states work.
* User actions use the correct semantic control and trigger the intended action.
* No accidental mocks, placeholders, debug code, dead branches, secrets,
  credentials, or machine-specific values are committed.
* No obvious duplicate requests, races, stale state, hydration mismatch,
  destructive retry, data corruption, or unbounded work is introduced.
* Existing testing or verification conventions are updated when applicable.

## 2. Foundations and HTML

### Required

* Standalone documents use the HTML doctype and declare UTF-8 early.
* The root `html` element has the correct valid language.
* Mobile pages declare a viewport without disabling zoom.
* Every document has exactly one meaningful non-empty title.
* The page has a coherent landmark structure and one primary `main`.
* Elements match their purpose: anchors navigate, buttons act, headings structure
  content, lists represent lists, and tables represent tabular data.
* Heading levels form a coherent outline.
* Published URLs remain stable unless the task includes a migration.

### Recommended when applicable

* Indexable pages have distinct descriptions and correct canonicals.
* Shareable pages provide coherent Open Graph metadata.
* Favicons, application icons, theme colour, and colour-scheme metadata match the
  implemented product.
* Feeds are discoverable and use stable item identifiers.
* Native popovers, dialogs, container queries, balanced wrapping, anchor
  positioning, and declarative invokers are preferred when they simplify the
  solution and meet support requirements.

### Avoid

* Clickable generic elements when native controls fit.
* Manual line breaks used only to force responsive wrapping.
* Custom JavaScript focus or positioning machinery when a reliable native
  primitive already solves the problem.

## 3. SEO and public discoverability

Apply primarily to public indexable content, not private or authenticated routes.

### Required when applicable

* Redirect status matches permanence and avoids loops or needless chains.
* Missing content returns a real 404, not a soft 404.
* Indexing policy deliberately distinguishes public, private, staging, duplicate,
  and thin content.
* Public primary content and metadata are present in the initial crawlable HTML
  when client-only rendering would prevent discovery.
* Heading structure communicates the page topic.
* Changed public URLs have appropriate redirects.

### Recommended when applicable

* `robots.txt` accurately represents crawl policy.
* Sitemaps contain canonical indexable URLs; large sites use sitemap indexes.
* URLs are lowercase, descriptive, shallow, and consistently hyphenated.
* Internal links use crawlable anchors and useful link text.
* Structured data is valid, relevant, and consistent with visible content.
* Breadcrumbs match the actual hierarchy.
* Image/video sitemap extensions and indexing notification protocols are used
  only when operationally justified.

### Avoid

* Soft 404s, wrong canonicals, duplicated metadata, broken internal links, and
  public primary content that depends on fragile client-side execution.

## 4. Accessibility

### Required

* Text and meaningful UI have sufficient contrast in all supported states.
* Every image has an appropriate `alt`: descriptive when informative, empty when
  decorative.
* Every form control has a programmatically associated label.
* All interactions work by keyboard in a logical order without traps.
* Focus is visibly indicated.
* Repeated navigation can be bypassed with a working skip link where applicable.
* Semantic HTML and landmarks expose structure.
* Links describe their destination or purpose.
* Every button and link has an accessible name, including icon-only controls.
* Form errors are textual, associated with the field, and announced when needed.
* Document and inline language are marked correctly.
* Motion respects `prefers-reduced-motion`.
* Audio/video provide required captions, transcripts, or descriptions.
* Data tables use real table structure, accessible naming, and header
  relationships.
* Pointer targets meet the applicable WCAG 2.2 minimum or have enough spacing.
* Background content becomes inert while a blocking modal is open.

### Recommended when applicable

* Prefer native `button`, `a`, `details`, `summary`, `dialog`, form, and popover
  behaviour.
* Add ARIA only when native semantics are insufficient.
* Authentication supports password managers and paste and avoids cognitive
  puzzles as the only route.
* Previously supplied information is not requested again unnecessarily.
* Mobile fields use suitable `type`, `autocomplete`, `inputmode`, and
  `enterkeyhint`.
* Collapsible content remains findable.
* Forced-colours mode preserves meaning and operability.

### Avoid

* Accessibility overlay widgets as a substitute for accessible code.
* Placeholder-only labels.
* Removed focus outlines without replacement.
* Positive `tabindex` used to repair DOM order.
* Empty controls or contradictory ARIA roles.

## 5. Security

Apply infrastructure checks only when relevant configuration is visible.

### Required when applicable

* Production is HTTPS-only with modern TLS.
* HSTS is enabled deliberately after HTTPS is valid for the relevant hosts.
* Responses prevent MIME sniffing and untrusted framing.
* Cookies use `Secure`, explicit `SameSite`, and `HttpOnly` whenever JavaScript
  access is unnecessary; session scope and prefixes are appropriately restricted.
* User-controlled values are validated or escaped for their HTML, script, style,
  URL, SQL, command, and DOM contexts.
* Authentication and authorisation are enforced at a trusted boundary, not only
  by client-side UI.
* Secrets and privileged credentials are neither committed nor shipped to the
  browser.
* Uploads, downloads, redirects, and external navigation validate untrusted
  values.
* Mixed active content is not introduced.

### Recommended when applicable

* CSP restricts scripts, styles, images, frames, connections, and embedding
  without exceptions that effectively disable it.
* Security-policy reports avoid sensitive infrastructure details.
* `Referrer-Policy` limits cross-origin URL leakage.
* `Permissions-Policy` disables unused powerful capabilities.
* Cross-origin isolation is enabled only when compatible.
* Mutable third-party assets use Subresource Integrity.
* Trusted Types protect material client-side DOM injection surfaces.
* `/.well-known/security.txt` provides a disclosure route.
* Logout clears sensitive local state where required.
* DNS CAA and DNSSEC are considered at the infrastructure level.

### Avoid

* Unsafe DOM injection with untrusted strings.
* Broad CSP wildcards, routine `unsafe-eval`, or unnecessary `unsafe-inline`.
* Security enforced only by hiding UI.
* Long-lived secrets in public runtime configuration.
* Disabling browser protections merely to satisfy an integration.

## 6. Well-known resources

These are contextual, not universal requirements.

### Recommended when applicable

* Standard metadata uses registered `/.well-known/` locations.
* Account-based sites expose a change-password redirect.
* Identity providers publish valid OpenID discovery metadata.
* Hosts with several APIs expose a machine-readable catalogue when useful.
* Apple/Android association files contain the exact intended apps, domains,
  paths, and signing identities.
* Federated products expose the discovery resources required by their protocol.

### Optional

* Related-origin WebAuthn metadata, NodeInfo, traffic advice, and other
  specialised protocol files.

Do not penalise an ordinary website for omitting unrelated resources.

## 7. Agent readiness

Apply to public information, documentation, catalogues, APIs, and products that
target agent discovery.

### Required when applicable

* Public URLs remain stable.
* Crawler rules do not contradict intended public/private access.

### Recommended when applicable

* Semantic HTML and structured data expose entities and relationships.
* Important content has suitable JSON, RSS, or Markdown alternatives.
* `/llms.txt` or an equivalent curated index points to authoritative content when
  useful.
* Per-page source representations use predictable discovery.
* AI crawler policy is explicit.
* HTTP `Link` headers advertise feeds, sitemaps, machine-readable alternatives,
  or tool endpoints where useful.
* Skill/API discovery metadata accurately describes callable capabilities.

### Optional

* Full-content bundles, bot authentication, MCP, A2A, WebMCP, agent cards,
  DNS-based discovery, AI catalogues, or conversational endpoints.

Emerging conventions do not reduce the score unless requested.

## 8. Performance

Do not claim Core Web Vitals were measured from a static diff.

### Required when applicable

* The implementation does not create a credible regression against LCP ≤ 2.5 s,
  INP ≤ 200 ms, and CLS ≤ 0.1 at the 75th percentile.
* Images use suitable dimensions and efficient formats and reserve layout space.
* The likely LCP resource is not lazy-loaded.
* Fingerprinted assets use long immutable caching; HTML and personalised
  responses use appropriate revalidation.
* Text resources are compressed by the delivery layer.
* No obvious layout shift, excessive main-thread work, request waterfall,
  unbounded rendering, or disproportionate bundle growth is introduced.

### Recommended when applicable

* Off-screen images, frames, and media are lazy-loaded.
* Critical preloads and preconnects are selective.
* Cacheable responses support validators and conditional requests.
* Fonts use efficient formats, appropriate subsetting and `font-display`, without
  excessive preloading.
* Render-blocking CSS and scripts are reduced safely.
* Scripts use `module`, `defer`, or `async` according to dependency and order.
* Back/forward-cache eligibility is preserved.
* Expensive off-screen rendering uses containment or visibility primitives when
  beneficial.
* Mobile full-height layouts use appropriate viewport units.
* Scrollbar changes do not create avoidable layout shift.
* Server timing reveals no sensitive details.

### Avoid

* Lazy-loading the LCP element.
* Domain sharding or image sprites retained for HTTP/1.1 request limits.
* Blanket preload/prefetch.
* Unnecessary synchronous third-party scripts in the head.
* Scroll/resize listeners where CSS or observation APIs safely fit.
* Performance claims unsupported by the project's measurement workflow.

## 9. Privacy

### Required when applicable

* Privacy disclosures match personal-data collection, purpose, legal basis,
  sharing, retention, and user rights.
* Non-essential cookies or storage wait for valid consent where opt-in is
  required.
* Rejecting consent is not materially harder than accepting it.
* Consent state is respected by scripts, embeds, tags, and later navigation.
* Personal or sensitive data does not leak through logs, URLs, analytics,
  bundles, errors, or public storage.
* The feature collects only the data it needs.

### Recommended when applicable

* Global Privacy Control and other legally relevant preference signals are
  honoured.
* Third-party scripts are justified, minimised, isolated, and consent-aware.
* Analytics are aggregate or privacy-preserving where sufficient.
* Retention and deletion match the stated policy.
* Cross-site embeds request storage access only after meaningful user action.

### Avoid

* Pre-consent tracking where consent is required.
* Consent dark patterns.
* Unnecessary third-party transmission.
* Collecting fields without a defined purpose.
* Sensitive data in public URLs.

## 10. Resilience

### Required when applicable

* Error pages return the correct status, explain the problem plainly, avoid
  leaking internals, and offer a next step.
* Network, API, and validation failures do not leave the UI stuck, destructive,
  or misleading.
* Partial failure does not corrupt valid state or duplicate a non-idempotent
  action.
* User-entered data is preserved when practical.

### Recommended when applicable

* Planned downtime returns 503 with a useful retry indication.
* Core content and primary navigation survive failure of non-essential
  JavaScript.
* Installable apps provide a valid manifest.
* Products promising offline use provide an intentional fallback and safe
  service-worker update strategy.
* Production-critical services use external monitoring and a separately hosted
  status surface.

### Avoid

* Returning 200 for error content.
* Raw stack traces or infrastructure details.
* Infinite retry loops or unsafe retries without idempotency control.
* Indiscriminate service-worker caching of authenticated or fast-changing data.

## 11. Internationalisation

Apply when multiple languages, regions, directions, or locales are supported.

### Required when applicable

* Document, inline language, and text direction match rendered content.
* Strings are not concatenated in ways that prevent translation or reordering.
* Dates, numbers, currencies, units, and plural forms are not hard-coded to one
  locale.

### Recommended when applicable

* One consistent multilingual URL strategy is used.
* `hreflang` alternates are valid, reciprocal, canonical, and correctly coded.
* Titles, descriptions, social metadata, structured data, and alt text are
  localised with the body.
* Locale switching is explicit and preserves the equivalent destination.
* Language names appear in their own language; flags do not stand for languages.
* CSS logical properties support RTL and alternative writing directions.
* Locale-aware APIs format dates, numbers, currency, units, lists, and plurals.
* Non-translatable brands, code, and identifiers remain unchanged.

### Avoid

* Automatic IP-based locale redirects that trap users or crawlers.
* English-only singular/plural assumptions.
* Hard-coded physical left/right throughout multilingual UI.
* Translated body content with metadata left in another language.

# Scoring

Start at 100. Deduct only for evidenced and applicable findings.

Suggested deductions:

* **Critical: 30–60** — exploitable security flaw, secret or personal-data
  exposure, authorisation bypass, destructive corruption, or fundamentally
  non-working change.
* **Major: 12–29** — broken primary flow, inaccessible core interaction, serious
  indexing/privacy failure, significant regression, or material Required
  violation.
* **Moderate: 4–11** — meaningful but limited defect.
* **Minor: 1–3** — small concrete issue.
* **Optional improvement: 0** — mention only when genuinely useful.

Score caps:

* Critical security flaw, secret exposure, authorisation bypass, or serious
  personal-data leak: maximum 25.
* Broken primary flow, inaccessible primary interaction, or major
  production/indexing/privacy failure: maximum 49.
* Any unresolved blocking issue: maximum 69.
* No blockers and only minor warnings: normally 90 or above.

Interpretation:

* **90–100**: production-quality for the requested scope.
* **75–89**: sound, with meaningful non-blocking improvements.
* **50–74**: substantial issues or at least one blocker.
* **25–49**: major failure or unsafe implementation.
* **0–24**: critically broken, dangerous, or unrelated.

Do not reduce the score for irrelevant features. Do not inflate it because the
patch is small.

## Blocking threshold

A finding blocks when the patch should not be accepted before correction,
including:

* requested behaviour that does not work;
* a material applicable Required violation;
* an Avoid pattern causing real harm;
* a security, privacy, accessibility, integrity, or destructive regression;
* unintended deindexing or exposure of private content;
* broken project contracts, buildability, or runtime integration.

Recommended items are normally non-blocking. Under `high` strictness they may
block when the task, constitution, production context, or acceptance criteria
depend on them.

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
"rationale": "Brief explanation of the score, applicable areas reviewed, and strongest evidence."
}

Rules:

* `score` is an integer from 0 to 100.
* `blocking_issues` and `warnings` are always arrays.
* Use repository-relative paths and line numbers when available.
* Make every finding self-contained and actionable.
* Do not include praise, generic advice, or optional wishlists as findings.
* Use an empty `blocking_issues` array when nothing blocks.
* Report insufficient evidence as a warning, not as an asserted failure.

# Attribution

Adapted, condensed, paraphrased, and reorganised for diff-based automated review
from **The Website Specification** checklist by Joost de Valk and contributors.

* Source: https://specification.website/checklist/
* Project: https://github.com/jdevalk/specification.website
* Source content licence: CC BY 4.0
* Changes: grouped and paraphrased checklist items; added applicability,
  strictness, evidence, blocking, and scoring rules for Looping Louie.

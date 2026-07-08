---
id: security
name: Security
category: security_review
description: >
  Provides application-security knowledge for authentication, authorisation,
  input validation, output encoding, secrets, sessions, data protection,
  dependency trust, abuse resistance, server boundaries, and secure deployment.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Security

## Scope

This skill covers security of web applications, APIs, services, integrations,
data flows, and deployment configuration.

It applies to:

- authentication and session management;
- authorisation and tenant isolation;
- server and API boundaries;
- untrusted input and output;
- browser security controls;
- secrets and configuration;
- file and URL handling;
- third-party services;
- dependency and supply-chain changes;
- logging and error handling;
- abuse, rate limits, and resource exhaustion;
- deployment and transport security.

Use the project's threat model, deployment architecture, and trust boundaries as
the source of truth.

# Security principles

## Trusted boundaries

Check that security decisions are enforced in trusted server-side code.

Client-side checks may improve user experience but must not be the only control
for:

- authentication;
- authorisation;
- ownership;
- tenant isolation;
- role restrictions;
- field-level access;
- pricing or entitlements;
- workflow state;
- destructive actions.

Never trust hidden UI, route guards, or client-provided metadata as proof of
permission.

## Least privilege

Check that:

- credentials have the smallest required scope;
- users receive only required permissions;
- service accounts cannot access unrelated resources;
- third-party tokens are limited by repository, tenant, environment, or action
  where supported;
- administrative operations are separated from ordinary application access;
- read and write capabilities are distinct where possible.

## Secure defaults

Check that:

- private is the default visibility;
- denial is the default when authorisation is uncertain;
- debug behaviour is disabled in production;
- new endpoints require explicit methods and permissions;
- cookies use secure defaults;
- generated links expire where appropriate;
- dangerous capabilities require deliberate enablement.

# Technical checks

## 1. Authentication

Check that:

- credentials are verified at a trusted boundary;
- session creation follows successful authentication;
- login errors do not unnecessarily reveal account existence;
- password and token comparison uses suitable secure mechanisms;
- password reset and magic links expire and are single-use where required;
- multifactor and one-time-code workflows prevent replay;
- account switching clears stale privileged state;
- logout invalidates or expires the relevant session;
- authentication rate limits and abuse controls exist where needed.

## 2. Authorisation

Check that every protected resource and mutation verifies:

- authenticated identity;
- required role or permission;
- resource ownership;
- tenant membership;
- field-level restrictions;
- current workflow state.

Apply checks to:

- single-resource endpoints;
- list and search endpoints;
- exports;
- bulk actions;
- background jobs;
- webhooks;
- indirect object references;
- cached responses.

Avoid relying on predictable IDs or obscurity.

## 3. Input validation

Treat all external input as untrusted, including:

- request bodies;
- query parameters;
- route parameters;
- headers;
- cookies;
- uploaded files;
- webhook payloads;
- third-party API responses;
- database content rendered in a new context;
- environment variables;
- model output.

Validate type, format, length, range, allowed values, and relationships.

Type annotations alone are not runtime validation.

## 4. Injection and output handling

Use context-appropriate safe APIs for:

- HTML and DOM;
- JavaScript;
- CSS;
- URLs;
- SQL;
- shell commands;
- templates;
- headers;
- logs;
- regular expressions.

Check that:

- HTML is escaped unless deliberately sanitised;
- DOM APIs do not inject untrusted strings unsafely;
- database queries use parameters;
- shell arguments avoid string interpolation;
- redirect destinations are allowlisted or constrained;
- log fields cannot forge entries;
- user input cannot create response splitting.

## 5. Sessions and cookies

Check that sensitive cookies use suitable:

- `Secure`;
- `HttpOnly`;
- explicit `SameSite`;
- path and domain scope;
- expiry;
- secure prefixes where appropriate.

Check that:

- session IDs are unpredictable;
- session rotation occurs after privilege changes;
- CSRF is addressed for cookie-authenticated mutations;
- client-readable storage does not contain long-lived secrets;
- logout and revocation affect all relevant sessions when required;
- stale sessions do not retain removed permissions.

## 6. Secrets and configuration

Check that secrets are not:

- committed;
- logged;
- returned in errors;
- embedded in frontend bundles;
- stored in public runtime configuration;
- copied into analytics;
- included in generated artifacts;
- exposed through build output.

Check that:

- secret names and environment variables are consistent;
- production does not depend on local `.env` loading;
- credentials are rotated and scoped;
- fallback values do not silently disable security;
- test credentials cannot reach production systems.

## 7. Files, uploads, and downloads

Check that:

- file type is verified beyond extension;
- size and count are bounded;
- filenames are normalised;
- paths cannot escape intended directories;
- uploaded content is stored outside executable locations;
- active content is served safely;
- downloads verify authorisation;
- signed links expire and are scoped;
- archives cannot create path traversal or decompression bombs;
- image and document processing libraries are treated as attack surfaces.

## 8. URLs, redirects, and outbound requests

Check that:

- redirects cannot target arbitrary untrusted destinations;
- outbound requests cannot access internal networks unexpectedly;
- protocol, host, port, and path are constrained;
- credentials are not forwarded to user-controlled origins;
- DNS rebinding and redirect chains are considered for SSRF-sensitive flows;
- webhook callback destinations are verified;
- public URLs do not contain secrets.

## 9. Browser protections

Where relevant, check:

- HTTPS;
- HSTS;
- `X-Content-Type-Options`;
- frame restrictions;
- Content Security Policy;
- referrer policy;
- permissions policy;
- secure cross-origin configuration;
- Subresource Integrity for mutable third-party assets;
- Trusted Types for material DOM-injection surfaces.

Do not weaken protections merely to satisfy an integration.

## 10. CORS and cross-origin behaviour

Check that:

- trusted origins are explicit;
- credentials are not allowed with broad origins;
- methods and headers are limited;
- preflight behaviour matches the endpoint;
- private APIs are not exposed through permissive defaults;
- origin validation cannot be bypassed by suffix or substring matching.

CORS is not an authentication mechanism.

## 11. Data protection and tenancy

Check that:

- tenant identifiers are derived from trusted identity where possible;
- queries include tenant boundaries;
- caches partition private data correctly;
- exports and reports apply the same permissions as the UI;
- background work preserves identity and tenant context;
- temporary files and logs do not mix tenants;
- backups and replicas follow access controls.

## 12. Webhooks and asynchronous processing

Check that:

- webhook signatures are verified;
- timestamps or nonces prevent replay where needed;
- delivery is idempotent;
- event IDs are deduplicated durably;
- payload schema is validated;
- retries do not duplicate effects;
- processing failures remain observable;
- queues and workers enforce the same permissions and boundaries.

## 13. Dependencies and supply chain

Check that:

- new packages are necessary;
- package names and sources are correct;
- versions are compatible and maintained;
- lockfiles are updated;
- install scripts and native binaries are understood;
- dependencies do not enter client bundles unnecessarily;
- licences and provenance meet project policy;
- generated or vendored code is not trusted blindly.

## 14. Abuse and resource exhaustion

Check for:

- rate limits;
- request-size limits;
- pagination bounds;
- query complexity limits;
- upload limits;
- concurrency controls;
- queue bounds;
- timeout budgets;
- expensive repeated operations;
- unbounded recursion or iteration;
- fan-out to external services.

Protect shared resources before exhaustion occurs.

## 15. Errors and logging

Check that:

- unexpected failures do not expose stack traces or internals;
- validation failures use appropriate 4xx responses;
- authorisation failures do not reveal protected data;
- caught errors are not returned as successful responses;
- logs contain enough context for investigation;
- credentials and sensitive payloads are redacted;
- security events are auditable;
- identifiers support correlation without exposing unnecessary personal data.

# High-risk patterns

Pay particular attention to:

- client-only authorisation;
- public secrets;
- cross-tenant data access;
- unsafe HTML or DOM injection;
- SQL or shell interpolation;
- arbitrary outbound URLs;
- insecure file paths;
- cookie-authenticated mutations without CSRF protection;
- permissive CORS with credentials;
- unsigned or replayable webhooks;
- private data in shared caches;
- unbounded expensive endpoints.

# Common false positives

Do not treat these as defects without context:

- absence of CSP in code when headers are managed by deployment infrastructure;
- use of client-side route guards in addition to server authorisation;
- public identifiers that are not used as access controls;
- a third-party dependency with no demonstrated vulnerable path;
- missing rate limits on a cheap, authenticated, low-volume internal operation.

# Output qualities

A secure implementation:

- enforces trust boundaries server-side;
- validates untrusted input;
- uses least privilege;
- protects secrets and sessions;
- preserves tenant isolation;
- resists common injection and abuse paths;
- fails without exposing sensitive information;
- remains compatible with the deployment environment.

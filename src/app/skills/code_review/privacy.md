---
id: privacy
name: Privacy
category: compliance_review
description: >
  Provides privacy knowledge for data minimisation, purpose limitation, consent,
  transparency, retention, deletion, user rights, logging, analytics, storage,
  third-party sharing, and privacy-preserving product design.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Privacy

## Scope

This skill covers privacy risks and requirements arising from collection,
storage, use, transmission, inference, retention, and deletion of personal data.

It applies to:

- forms and account creation;
- authentication and identity;
- analytics and tracking;
- cookies and browser storage;
- logs and monitoring;
- user-generated content;
- AI and automated processing;
- third-party integrations;
- data exports and imports;
- customer support tooling;
- retention and deletion workflows;
- public URLs and shared content.

This skill identifies engineering and product privacy concerns. It does not
replace qualified legal advice.

# Privacy principles

## Data minimisation

Check that:

- every collected field has a defined purpose;
- the feature does not collect data merely because it may be useful later;
- optional data is clearly optional;
- derived or inferred data is treated as personal data when it can identify or
  profile a person;
- full records are not transmitted when a subset is sufficient;
- test and development environments avoid unnecessary production personal data;
- analytics events exclude unnecessary identifiers and content.

## Purpose limitation

Check that:

- data is used for the purpose communicated to the user;
- a new feature does not silently repurpose existing data;
- secondary uses are documented and justified;
- access controls reflect the intended purpose;
- product defaults do not encourage unrelated use;
- training, profiling, advertising, or enrichment are not introduced implicitly.

## Transparency

Check that users can understand:

- what data is collected;
- why it is collected;
- who receives it;
- how long it is retained;
- whether automated decisions or inference occur;
- how to access, correct, export, or delete it;
- which choices are optional;
- what happens when consent is withdrawn.

Privacy notices must match actual system behaviour.

## Lawful basis and consent

Where consent is required, check that:

- consent is obtained before non-essential processing starts;
- acceptance is not preselected;
- rejection is not materially harder than acceptance;
- consent choices are specific enough for the processing;
- withdrawal is available and respected;
- later navigation does not reactivate declined processing;
- third-party tags and embeds remain blocked until permitted;
- proof of consent is stored only as necessary.

Do not use consent as a default explanation for processing that depends on
another lawful basis.

## Sensitive and high-risk data

Apply stronger scrutiny to:

- health information;
- financial information;
- identity documents;
- precise location;
- biometric data;
- children's data;
- communications content;
- employment and performance data;
- political or religious information;
- criminal or legal information;
- credentials and authentication secrets.

Check whether the feature can avoid collecting or exposing the data at all.

# Technical checks

## 1. Data inventory and flow

Identify:

- data sources;
- fields collected;
- derived attributes;
- storage locations;
- processors and recipients;
- geographic transfers;
- retention periods;
- deletion paths;
- logs, backups, caches, and exports.

A privacy-sensitive change should have a comprehensible data flow.

## 2. Browser storage and cookies

Check that:

- non-essential storage waits for consent where required;
- authentication secrets are not stored in JavaScript-readable storage without
  architectural necessity;
- local storage does not retain sensitive content indefinitely;
- logout and account switching clear sensitive local state;
- storage keys do not reveal unnecessary personal information;
- browser caches do not expose private responses;
- shared-device scenarios are considered.

## 3. URLs and navigation

Check that personal or sensitive data does not appear in:

- query strings;
- URL paths;
- fragments;
- referrer headers;
- redirect targets;
- analytics page names;
- browser history;
- copied share links.

Use opaque identifiers when a public or semi-public URL requires an identifier.

## 4. Logging and observability

Check that logs, traces, metrics, and error reports do not contain:

- credentials;
- tokens;
- full request bodies;
- personal messages;
- identity documents;
- sensitive form values;
- complete user records;
- unnecessary IP addresses or device identifiers.

Use redaction, structured allowlists, and retention limits.

Operational usefulness does not justify unrestricted logging.

## 5. Third-party services

Check that:

- each third party has a defined purpose;
- only required data is sent;
- credentials and identifiers are scoped;
- the provider's retention and reuse align with the product commitment;
- failure does not cause data to be sent elsewhere unexpectedly;
- consent state reaches the integration;
- user deletion propagates where required;
- processor changes do not silently expand data use.

## 6. Access control and tenancy

Check that:

- personal data is authorised at a trusted server boundary;
- tenant boundaries are enforced independently of client input;
- list, search, export, and bulk endpoints apply the same restrictions;
- support and administrator access is limited and auditable;
- temporary links expire;
- shared artifacts expose only intended fields;
- account switching clears stale data.

## 7. Retention and deletion

Check that:

- retention has an explicit duration or criterion;
- temporary data expires;
- deleted accounts do not remain active in auxiliary systems;
- backups and archives follow a documented deletion model;
- logs have shorter retention when possible;
- legal or contractual holds are handled explicitly;
- deletion is not implemented only as hidden UI state;
- derived data and embeddings are considered.

## 8. User rights and control

Where applicable, check that users can:

- access their data;
- correct inaccurate data;
- export it in a useful format;
- delete it;
- object or opt out;
- withdraw consent;
- understand automated processing;
- appeal material automated decisions.

The implementation should not require manual engineering work for routine
rights requests when the product promises self-service control.

## 9. Analytics and experimentation

Check that:

- events contain only required attributes;
- free-text content is not captured by default;
- identifiers are pseudonymous where sufficient;
- experiments do not expose sensitive cohorts;
- session replay masks sensitive fields;
- analytics remain disabled when consent is declined;
- retention and access are limited;
- product metrics can be achieved with aggregate data where possible.

## 10. AI and model processing

Check that:

- prompts do not include unnecessary personal data;
- provider retention and training settings match product commitments;
- user content is not reused silently;
- sensitive output is not exposed to other tenants;
- generated summaries do not reveal hidden source data;
- embeddings, traces, and evaluations follow retention and deletion rules;
- automated decisions have appropriate human control where material;
- model logs do not become an uncontrolled secondary data store.

## 11. Public and collaborative features

Check that:

- default visibility is appropriate;
- users understand who can access shared content;
- public links expose only intended information;
- indexing is disabled for private content;
- revocation invalidates access;
- collaboration invitations are scoped;
- comments and activity feeds do not reveal hidden metadata;
- notifications avoid sensitive content on lock screens or email previews where
  inappropriate.

## 12. International transfer and localisation

Where data crosses regions, check that:

- the transfer is intentional;
- regional deployment commitments are respected;
- providers and subprocessors match contractual requirements;
- fallback infrastructure does not move data unexpectedly;
- support tooling does not bypass residency controls.

Do not infer legal compliance solely from deployment geography.

# Privacy-by-design checks

Check that the proposal:

- collects the minimum data;
- uses privacy-preserving defaults;
- limits visibility;
- separates identity from activity where possible;
- avoids public identifiers;
- supports deletion and correction;
- prevents secondary use;
- minimises third-party transmission;
- includes retention;
- makes user choices understandable.

# High-risk patterns

Pay particular attention to:

- secrets or personal data in public configuration;
- sensitive data in URLs;
- pre-consent tracking;
- cross-tenant data exposure;
- full payload logging;
- public indexing of private content;
- unbounded retention;
- third-party SDKs receiving more data than required;
- user deletion that ignores copies, logs, or derived data;
- AI providers receiving unnecessary personal data.

# Common false positives

Do not treat these as defects without applicable requirements:

- absence of a consent banner when no consent-dependent processing exists;
- use of aggregate analytics without personal identifiers;
- retention required by an explicit legal or contractual obligation;
- administrator access that is limited, necessary, and audited;
- temporary operational logs containing non-sensitive identifiers under a
  defined retention period.

# Output qualities

A privacy-respecting design is:

- minimal;
- transparent;
- purpose-bound;
- controllable by users;
- limited in retention;
- secure in access;
- cautious with third parties;
- explicit about data flows and deletion.

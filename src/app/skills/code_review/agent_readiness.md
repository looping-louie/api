---
id: agent_readiness
name: Agent Readiness
category: machine_readability_review
description: >
  Provides agent-readiness knowledge for semantic content, stable URLs,
  machine-readable representations, discovery metadata, API and tool contracts,
  crawler policy, provenance, structured output, and safe automation.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Agent Readiness

## Scope

This skill covers how effectively software, documentation, content, and APIs can
be discovered, understood, and used by automated agents.

It applies to:

- public documentation;
- product and service catalogues;
- APIs and tools;
- structured content;
- machine-readable exports;
- agent-facing workflows;
- callable capabilities;
- discovery metadata;
- automation-safe operations;
- provenance and freshness.

Agent readiness is contextual. Do not require emerging protocols for ordinary
websites or private applications that do not target machine use.

# Core principles

## Stable identity

Agents need durable identifiers for:

- pages;
- entities;
- documents;
- API resources;
- tools;
- versions;
- events;
- artifacts.

Check that:

- URLs are stable;
- identifiers are unique;
- redirects preserve moved resources;
- temporary implementation details do not define public identity;
- canonical representations are discoverable;
- versions and deprecations are explicit.

## Semantic clarity

Check that content exposes:

- clear headings;
- meaningful labels;
- explicit relationships;
- structured lists and tables;
- machine-readable status;
- consistent terminology;
- unambiguous units and formats.

Avoid relying only on visual position, icons, colour, or undocumented convention.

## Structured alternatives

Where useful, check that important content has machine-readable forms such as:

- JSON;
- RSS or Atom;
- Markdown;
- CSV;
- schema-based exports;
- API responses;
- structured data.

The machine-readable representation should match the human-visible source.

# Technical checks

## 1. Public content structure

Check that:

- semantic HTML represents content hierarchy;
- headings identify topics;
- links describe destinations;
- tables expose real relationships;
- dates use machine-readable values;
- status and availability are explicit;
- entities have stable canonical URLs;
- primary content is not hidden behind fragile client-only execution;
- pagination and continuation are discoverable.

## 2. Machine-readable representations

Check that:

- representations use documented schemas;
- field names remain stable;
- types and nullability are clear;
- dates and times use explicit formats and time zones;
- units and currencies are explicit;
- pagination is deterministic;
- errors are structured;
- optional and required fields are distinguishable;
- examples match real output;
- additional commentary does not corrupt strict JSON or CSV output.

## 3. Discovery

Where the product targets agents, check that:

- authoritative resources are linked from canonical pages;
- HTTP `Link` headers advertise alternate formats where useful;
- feeds and sitemaps are discoverable;
- API or tool catalogues describe available capabilities;
- `/llms.txt` or an equivalent curated index is accurate when used;
- per-page source representations follow a predictable convention;
- discovery files do not expose private endpoints;
- discovery metadata remains current.

Emerging conventions should not be added without a concrete consumer.

## 4. Tool and API contracts

Check that callable capabilities define:

- name;
- purpose;
- input schema;
- required fields;
- output schema;
- authentication;
- side effects;
- idempotency;
- failure modes;
- limits;
- version;
- examples.

Descriptions should be specific enough for an agent to choose the correct tool.

Avoid overlapping tools with indistinguishable descriptions.

## 5. Safe automation

Check that agent-callable operations:

- require explicit authorisation;
- validate all input;
- distinguish read and write actions;
- identify destructive effects;
- support confirmation where appropriate;
- use idempotency for retryable mutations;
- expose deterministic status;
- avoid hidden side effects;
- bound cost, time, and resource use;
- preserve auditability.

Agents must not receive broader permissions than required.

## 6. Crawler and access policy

Check that:

- public and private access are distinguished;
- crawler policy matches intended discoverability;
- `robots.txt` is not treated as confidentiality;
- AI-specific crawler rules are explicit where needed;
- authenticated content is protected at a trusted boundary;
- rate limits and terms do not conflict with advertised access;
- machine-readable endpoints do not bypass ordinary authorisation.

## 7. Provenance and authority

Check that machine-consumed content can identify:

- authoritative source;
- publication or generation time;
- last update;
- version;
- owner or publisher;
- applicable locale;
- source references where needed;
- confidence or uncertainty where relevant.

Generated summaries should not obscure their source material.

## 8. Freshness and invalidation

Check that:

- stale content is identifiable;
- cache headers match freshness;
- update timestamps reflect meaningful changes;
- removed resources return appropriate status;
- consumers can detect changed versions;
- feeds or webhooks avoid duplicate processing;
- pagination and cursors remain stable during updates;
- agent indexes can discover canonical replacements.

## 9. Documentation quality

Check that documentation:

- starts with purpose and intended user;
- defines terminology;
- includes complete examples;
- describes authentication;
- explains errors;
- identifies limits;
- distinguishes stable and experimental features;
- documents versioning and deprecation;
- does not rely on screenshots for essential information;
- remains consistent with implementation.

## 10. Structured generation

For model-generated artifacts, check that:

- the output contract is explicit;
- JSON is valid;
- required keys are present;
- extra keys are controlled;
- enumerated values are constrained;
- Markdown headings follow the required order;
- maximum length is enforceable;
- repair or retry exists for malformed structured output;
- local deterministic validation complements model validation;
- downstream consumers do not parse informal prose.

## 11. Identity and entity resolution

Check that:

- names are not the only identifiers;
- aliases and historical identifiers are handled;
- references are unambiguous;
- duplicate entities can be reconciled;
- tenant boundaries remain explicit;
- external identifiers include their namespace;
- merged and deleted entities preserve redirects or tombstones where needed.

## 12. Internationalisation

For multilingual content, check that:

- locale is explicit;
- alternate-language resources are linked;
- machine-readable values remain canonical;
- translated labels do not replace stable identifiers;
- dates, numbers, and units remain parseable;
- language fallback is documented;
- agent discovery does not treat partial translations as complete equivalents.

## 13. Privacy and security

Check that:

- machine-readable representations do not expose additional private fields;
- discovery files omit secrets;
- tool descriptions do not reveal internal infrastructure unnecessarily;
- agent logs follow privacy rules;
- external agents receive scoped credentials;
- user content is not made public for discoverability;
- prompt or tool output cannot escalate permission;
- untrusted model output is validated before execution.

# High-risk patterns

Pay particular attention to:

- undocumented side effects;
- overlapping ambiguous tools;
- invalid structured output;
- public discovery of private endpoints;
- machine-readable exports containing more data than the UI;
- unstable identifiers;
- missing versioning;
- no idempotency for retryable writes;
- agents acting on unvalidated model output;
- documentation examples that disagree with the implementation.

# Common false positives

Do not treat these as defects without a concrete agent use case:

- absence of `/llms.txt`;
- absence of MCP, A2A, WebMCP, or agent cards;
- absence of alternate Markdown for a small ordinary website;
- lack of public API discovery for a private internal service;
- absence of structured data where no consumer exists;
- a human-only workflow that deliberately requires judgement and confirmation.

# Output qualities

An agent-ready system:

- has stable identities;
- exposes clear semantics;
- provides reliable structured representations;
- documents callable capabilities;
- validates automated actions;
- preserves provenance and freshness;
- distinguishes public and private access;
- remains safe under retries and partial failure.

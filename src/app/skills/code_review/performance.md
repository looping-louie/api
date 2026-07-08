---
id: performance
name: Performance
category: performance_review
description: >
  Provides performance knowledge for rendering, Core Web Vitals, JavaScript,
  CSS, images, fonts, network requests, caching, payload size, server latency,
  runtime work, and measurement-driven optimisation.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Performance

## Scope

This skill covers user-perceived and system performance of web applications,
websites, APIs, and supporting delivery infrastructure.

It applies to:

- page loading and rendering;
- Core Web Vitals;
- JavaScript execution;
- CSS and layout;
- images, video, and fonts;
- data fetching and waterfalls;
- caching and compression;
- server latency;
- bundle composition;
- repeated work and memory growth;
- background processing;
- performance measurement.

A static review can identify credible risks but cannot prove measured
performance improvements.

# Performance principles

## Measure the relevant outcome

Use evidence appropriate to the target:

- field data for real-user experience;
- lab tests for reproducible diagnosis;
- bundle analysis for shipped code;
- server timing and tracing for backend latency;
- profiling for main-thread work;
- load tests for capacity;
- database analysis for query behaviour.

Do not claim Core Web Vitals or throughput improvements without measurement.

## Optimise the critical path

Prioritise work that affects:

- initial rendering;
- primary content;
- first interaction;
- navigation;
- critical mutations;
- high-volume endpoints;
- constrained devices or networks.

Avoid optimising rare code while leaving the main path slow.

# Technical checks

## 1. Largest Contentful Paint

Check that:

- likely LCP content is discoverable early;
- the LCP image is not lazy-loaded;
- responsive image candidates are appropriate;
- critical resources are not hidden behind client-side rendering unnecessarily;
- server response time is reasonable;
- render-blocking styles and scripts are controlled;
- font loading does not delay primary content unnecessarily;
- preload is used selectively and correctly.

## 2. Interaction to Next Paint

Check that:

- input handlers avoid long synchronous work;
- expensive work is split, deferred, or moved off the main thread where
  appropriate;
- repeated rendering is bounded;
- event delegation is used where it reduces overhead;
- debouncing or throttling is applied only when semantically correct;
- large lists use suitable rendering strategies;
- third-party scripts do not monopolise the main thread;
- transitions and state updates remain responsive.

## 3. Cumulative Layout Shift

Check that:

- images and media reserve dimensions;
- ads, embeds, and async content reserve space;
- fonts do not cause excessive metric changes;
- sticky and fixed elements do not shift content unexpectedly;
- banners and notices use intentional placement;
- client-only fallbacks preserve dimensions;
- dynamic insertion does not move already visible controls.

## 4. Images and media

Check that:

- dimensions match display needs;
- responsive images provide useful candidates;
- modern formats are used where supported;
- compression is appropriate;
- off-screen media is lazy-loaded;
- the LCP asset is prioritised;
- decorative assets are not oversized;
- video does not load unnecessary data before interaction;
- placeholders do not cost more than the asset they replace.

## 5. Fonts

Check that:

- font files use efficient formats;
- character subsets match actual usage;
- too many families, weights, and styles are not loaded;
- `font-display` matches the product need;
- preload is limited to critical fonts;
- fallback metrics reduce layout shift;
- icon fonts are not used when smaller alternatives fit;
- remote font dependencies do not create unnecessary connection cost.

## 6. JavaScript

Check that:

- route-level splitting remains effective;
- large feature dependencies are lazy-loaded;
- browser-only libraries do not enter server bundles;
- tree shaking is not defeated;
- entire icon, locale, editor, chart, or SDK collections are not imported;
- polyfills match the support policy;
- global plugins remain small;
- listeners, observers, timers, and subscriptions are cleaned up;
- repeated navigation does not multiply work;
- serialisation does not ship large unused state.

## 7. CSS

Check that:

- critical styles are available when needed;
- unused global styles do not grow unchecked;
- selector complexity remains reasonable;
- expensive layout patterns are not repeated at scale;
- animation uses suitable properties;
- layout thrashing is avoided;
- container and visibility primitives are used where beneficial;
- style recalculation is not triggered repeatedly by JavaScript.

## 8. Network and data fetching

Check that:

- independent requests run in parallel;
- avoidable waterfalls are removed;
- duplicate fetches are not introduced;
- payloads contain only required fields;
- pagination and limits bound response size;
- speculative prefetching is selective;
- connections are reused;
- preconnect is limited to important origins;
- retries are bounded;
- cancelled or stale requests stop unnecessary work where possible.

## 9. Caching

Check that:

- fingerprinted static assets use long immutable caching;
- HTML uses appropriate revalidation;
- private and personalised responses are not cached publicly;
- cache keys include required variation;
- locale, tenant, permission, and experiment state do not collide;
- stale-while-revalidate or ISR matches freshness requirements;
- invalidation is possible when data changes;
- in-memory cache assumptions match the deployment topology.

Caching incorrect or private data is worse than not caching.

## 10. Compression and transport

Check that:

- text assets are compressed;
- Brotli or gzip is configured appropriately;
- HTTP versions and connection behaviour match the host;
- unnecessary redirects are removed;
- response headers are not excessively large;
- chunking and streaming are used when useful;
- server timing does not expose sensitive internals.

## 11. Server and API performance

Check that:

- database queries are bounded;
- indexes support common access patterns;
- N+1 queries are avoided;
- external calls have timeouts;
- independent work runs concurrently where safe;
- expensive operations use background processing when the response need not wait;
- request work is bounded;
- large exports use streaming or asynchronous delivery;
- serverless cold-start assumptions are realistic;
- process-local state does not create scaling bottlenecks.

## 12. Memory and lifecycle

Check that:

- subscriptions are released;
- caches are bounded;
- queues are bounded;
- large objects are not retained accidentally;
- repeated navigation or requests do not leak memory;
- file handles and streams close;
- long-running processes expose memory growth;
- per-request state does not accumulate globally.

## 13. Third-party code

Check that:

- every third-party script has a clear purpose;
- loading strategy matches criticality;
- synchronous head scripts are avoided where possible;
- consent requirements are respected;
- failure does not block core functionality;
- tag managers do not bypass performance controls;
- third-party origins are limited;
- the cost is measured rather than assumed.

## 14. Mobile and constrained environments

Check that:

- layouts avoid excessive work on resize and scroll;
- touch interaction remains responsive;
- images match small viewports;
- low-memory devices are considered;
- offline or poor-network states do not trigger repeated work;
- full-height layouts use suitable viewport units;
- battery-intensive polling or animation is bounded.

## 15. Testing and budgets

Where the project uses performance controls, check that:

- bundle budgets remain enforced;
- critical route metrics have regression thresholds;
- load tests reflect expected concurrency;
- performance tests run against production-like builds;
- measurements are repeatable;
- observed regressions produce actionable diagnostics.

# High-risk patterns

Pay particular attention to:

- lazy-loading the LCP resource;
- large global bundles;
- duplicate initial requests;
- serial request waterfalls;
- unbounded lists or polling;
- layout shift from missing dimensions;
- expensive third-party scripts;
- public caching of private responses;
- memory leaks across navigation;
- unsupported performance claims.

# Common false positives

Do not treat these as defects without evidence:

- a small dependency imported on every route;
- absence of a preload;
- absence of lazy loading for above-the-fold content;
- a simple implementation that is already fast enough;
- lack of a performance optimisation not required by the task;
- an unmeasured theoretical micro-optimisation.

# Output qualities

A performant implementation:

- prioritises the critical path;
- avoids unnecessary bytes and work;
- remains responsive;
- preserves layout stability;
- uses caching safely;
- bounds server and client resource use;
- is supported by measurement rather than intuition.

# SEO

## Scope

This skill covers organic search discoverability of public, indexable web
content.

It applies to:

- public pages and routes;
- rendering strategy;
- document metadata;
- canonical URLs;
- redirects and migrations;
- internal linking;
- structured data;
- sitemaps and robots rules;
- multilingual discovery;
- pagination and faceted navigation;
- error and duplicate content;
- performance where it affects search experience.

Do not apply SEO requirements to private, authenticated, administrative, or
deliberately non-indexable content.

# Technical checks

## 1. Crawlability

Check that:

- important public pages are reachable through crawlable anchors;
- navigation does not depend only on JavaScript event handlers;
- crawler rules do not block required assets or content;
- server responses are accessible without unsupported client execution;
- infinite spaces such as calendars, filters, and generated parameters are
  controlled;
- links use valid URLs;
- broken internal links are not introduced;
- authentication and geolocation do not block public content unintentionally.

## 2. Indexability

Check that:

- public pages intended for search are indexable;
- private, staging, duplicate, thin, search-result, and error pages are excluded
  deliberately;
- `noindex` is not contradicted by blocking crawl access;
- canonical and robots directives agree;
- client-side metadata updates are available in initial crawlable output when
  required;
- soft 404s are avoided;
- missing content returns a real 404 status;
- removed content uses the appropriate redirect or gone response.

## 3. Rendering

Check that:

- primary content exists in initial HTML when indexing requires it;
- metadata is present during initial rendering;
- hydration does not replace useful content with empty or error states;
- client-only rendering is a deliberate choice;
- prerendered routes include all required dynamic URLs;
- static deployments preserve real status codes where necessary;
- rendering varies safely by locale, device, or user state.

## 4. Titles and descriptions

Check that:

- every indexable page has a meaningful title;
- titles are distinct where page intent differs;
- descriptions reflect visible content;
- templates do not create duplicated or malformed metadata;
- dynamic values handle missing records;
- stale metadata does not persist after navigation;
- titles and descriptions are localised with the page;
- generated text remains concise and useful.

Metadata should describe the page, not merely repeat the site name.

## 5. Canonical URLs

Check that:

- each indexable page declares the preferred URL where duplicate variants exist;
- canonical URLs are absolute where required;
- canonicals point to indexable successful pages;
- pagination, filters, sorting, tracking parameters, and alternate routes are
  handled intentionally;
- HTTP and HTML canonicals agree;
- self-referencing canonicals are used consistently when part of the strategy;
- canonical targets do not cross tenants or environments.

A canonical is a hint, not an access-control mechanism.

## 6. Redirects and migrations

Check that:

- permanent moves use permanent redirects;
- temporary changes use temporary redirects;
- redirect chains are minimised;
- redirect loops are impossible;
- query parameters and path intent are preserved where needed;
- changed public URLs map to the most relevant destination;
- mass redirects do not send unrelated removed content to the home page;
- internal links are updated to final URLs;
- migrations account for canonicals, sitemaps, and alternate-language links.

## 7. URL design

Check that URLs are:

- stable;
- descriptive;
- consistently cased;
- consistently hyphenated;
- free of unnecessary parameters;
- shallow enough to remain understandable;
- independent from temporary implementation details;
- safe from personal or sensitive data exposure.

Do not change established public URLs without migration value.

## 8. Internal linking

Check that:

- important pages receive crawlable internal links;
- link text describes the destination;
- navigation reflects information hierarchy;
- orphan pages are avoided;
- breadcrumbs match the real hierarchy;
- related content links are relevant;
- links do not rely only on images without useful alternatives;
- disabled or placeholder links do not enter production.

## 9. Structured data

Check that:

- the selected vocabulary matches the visible content;
- required properties are present;
- values match what users can see;
- URLs are canonical;
- dates, prices, availability, and organisation details are accurate;
- user-generated content is not misrepresented;
- multiple schemas do not conflict;
- structured data is rendered in crawlable output;
- invalid or speculative markup is not added solely to seek rich results.

Structured data should describe reality, not manufacture eligibility.

## 10. Sitemaps

Where useful, check that:

- sitemaps contain canonical indexable successful URLs;
- removed, redirected, private, and `noindex` URLs are excluded;
- last-modified values reflect meaningful content changes;
- large sites use sitemap indexes;
- locale alternates are consistent;
- dynamic routes are included;
- sitemap generation works in the deployment environment;
- discovery through `robots.txt` or search-console configuration is intentional.

## 11. Robots rules

Check that:

- `robots.txt` matches the intended crawl policy;
- staging and private environments are protected beyond crawler directives;
- required assets remain crawlable;
- blocked paths do not prevent canonical or redirect discovery unnecessarily;
- wildcard and path rules target the intended routes;
- AI-specific crawler policy does not accidentally contradict search policy.

`robots.txt` does not provide confidentiality.

## 12. Error handling

Check that:

- missing resources return 404;
- permanently removed content uses 404, 410, or a relevant redirect;
- error pages do not become indexable duplicates;
- server failures return appropriate 5xx responses;
- maintenance uses 503 with retry guidance;
- error templates provide useful navigation;
- soft 404 content is not returned with 200.

## 13. Content and headings

Check that:

- the page has one clear primary topic;
- headings reflect content hierarchy;
- primary content is not hidden behind interaction unnecessarily;
- duplicated boilerplate does not overwhelm unique content;
- thin pages have a deliberate indexing decision;
- generated content is useful, accurate, and reviewed;
- visible content and metadata agree;
- important text is not embedded only in images.

## 14. Images and media

Check that:

- informative images have useful alternative text;
- filenames and surrounding text provide context where useful;
- image dimensions and delivery support performance;
- video pages expose relevant metadata and transcripts;
- image or video sitemap extensions are used only when justified;
- lazy loading does not hide primary media from discovery.

## 15. Multilingual SEO

Check that:

- locale URLs are consistent;
- `hreflang` values are valid and reciprocal;
- each alternate is canonical;
- regional variants are intentional;
- `x-default` has a clear purpose;
- language switching links to equivalent content;
- automatic redirects do not trap crawlers;
- metadata and structured data are translated;
- untranslated pages are not advertised as complete alternates.

## 16. Performance and search experience

Check that:

- likely LCP content loads promptly;
- layout shift does not disrupt reading or interaction;
- mobile pages remain usable;
- server latency does not prevent reliable crawling;
- essential content does not depend on failing third parties;
- performance changes are measured where the task targets them.

Do not claim ranking impact from theoretical performance changes alone.

# High-risk patterns

Pay particular attention to:

- accidental `noindex`;
- private content becoming indexable;
- soft 404s;
- wrong canonicals;
- client-only primary content;
- redirect loops or chains;
- public URL changes without redirects;
- invalid structured data;
- sitemap entries for redirected or private URLs;
- untranslated metadata;
- blocked assets required for rendering.

# Common false positives

Do not treat these as defects without context:

- absence of SEO metadata on private pages;
- absence of structured data where no relevant vocabulary exists;
- absence of a sitemap for a very small site with complete internal linking;
- client-side rendering in a private application;
- absence of a canonical on a unique page under a strategy that does not require
  explicit canonicals;
- lack of search optimisation for intentionally unindexed content.

# Output qualities

An SEO-ready implementation:

- is crawlable and indexable by design;
- exposes primary content and metadata reliably;
- uses stable canonical URLs;
- handles redirects and errors correctly;
- maintains useful internal linking;
- describes visible content accurately;
- respects multilingual and deployment constraints.

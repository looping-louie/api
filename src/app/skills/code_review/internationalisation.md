---
id: internationalisation
name: Internationalisation
category: web_review
description: >
  Provides internationalisation knowledge for language, locale, translation,
  pluralisation, formatting, multilingual routing, metadata, right-to-left
  layouts, writing systems, and locale-sensitive user experience.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Internationalisation

## Scope

This skill covers preparation and implementation for products that support
multiple languages, locales, regions, writing directions, or cultural
conventions.

It applies to:

- translated interfaces;
- multilingual public content;
- locale-specific routing;
- date, number, currency, unit, list, and plural formatting;
- right-to-left layouts;
- localised metadata;
- translated emails and notifications;
- user-generated multilingual content;
- regional pricing, legal text, and content.

Do not require internationalisation in a deliberately single-locale product
unless the task introduces locale-sensitive behaviour.

# Technical checks

## 1. Language and direction

Check that:

- the document language matches the rendered content;
- inline language changes are marked;
- text direction matches the language;
- right-to-left content uses `dir="rtl"` or equivalent document context;
- mixed-direction content remains readable;
- direction is not inferred from flags or country alone;
- user-generated content can declare or detect language safely where needed.

## 2. Translation architecture

Check that:

- user-facing strings are externalised consistently;
- translation keys remain stable;
- strings are not concatenated in ways that prevent reordering;
- placeholders are named clearly;
- translators receive enough context;
- HTML is not embedded in translations unnecessarily;
- rich text uses safe structured interpolation;
- fallback behaviour is intentional;
- missing translations are observable without exposing raw keys in production.

## 3. Pluralisation and grammar

Check that:

- plural rules use locale-aware mechanisms;
- zero, one, two, few, many, and other categories are supported where required;
- gender and grammatical case are not hard-coded to English assumptions;
- sentence fragments are not assembled across translation keys;
- counts and nouns can reorder;
- abbreviations and punctuation remain locale appropriate.

Avoid logic such as `count === 1 ? singular : plural` for multilingual products.

## 4. Dates and time

Check that:

- dates use locale-aware formatting;
- time zones are explicit where ambiguity matters;
- server and client do not render conflicting date formats;
- daylight-saving transitions are handled;
- relative time is localised;
- input and storage formats are distinguished;
- date pickers respect locale conventions without changing canonical storage;
- deadlines communicate the relevant time zone.

Use stable machine formats for transport and locale-aware formats for display.

## 5. Numbers, currencies, and units

Check that:

- numbers use locale-aware separators;
- currencies use correct symbols and placement;
- currency code is explicit where symbols are ambiguous;
- percentages are formatted by locale;
- units use locale-aware formatting where available;
- precision and rounding match product requirements;
- parsing does not assume one decimal separator;
- financial values are not converted implicitly.

## 6. Lists and names

Check that:

- natural-language lists use locale-aware conjunctions;
- personal names are not forced into first-name/last-name assumptions;
- addresses allow regional variation;
- postal codes and phone numbers are not validated with one-country rules unless
  the product is region-specific;
- sorting and collation use locale-aware behaviour where user-visible;
- search accounts for diacritics and normalisation as required.

## 7. Multilingual routing

For multilingual public sites, check that:

- one URL strategy is used consistently;
- locale prefixes, domains, or parameters are deliberate;
- switching locale preserves the equivalent destination;
- unsupported locales fail predictably;
- automatic detection does not trap users;
- users can override detected locale;
- locale choice persists appropriately;
- direct links and refreshes work;
- canonical URLs and redirects remain consistent.

Avoid mandatory IP-based redirects that prevent access to another locale.

## 8. SEO and metadata

Check that localised pages include localised:

- titles;
- descriptions;
- canonical URLs;
- Open Graph metadata;
- structured data;
- alternative text;
- breadcrumbs;
- social images where text is embedded.

For `hreflang`, check that:

- codes are valid;
- alternates are reciprocal;
- each alternate is canonical;
- regional and language variants are intentional;
- `x-default` is used only when appropriate;
- missing translations are not advertised as complete alternates.

## 9. Right-to-left and writing systems

Check that:

- CSS logical properties are used where direction may change;
- icons with directional meaning mirror when appropriate;
- non-directional icons do not mirror unnecessarily;
- navigation and progress direction remain understandable;
- text alignment follows content direction;
- truncation and wrapping support complex scripts;
- fonts contain required glyphs;
- line height accommodates script characteristics;
- bidirectional text does not expose spoofing or ordering problems.

Avoid hard-coded left and right for layout semantics.

## 10. Forms and input

Check that:

- labels and help text are translated;
- validation messages are localised;
- input modes match expected data;
- examples use local conventions;
- server validation accepts canonical and supported local formats;
- error messages do not expose untranslated backend strings;
- field order can vary by locale;
- names, addresses, and identifiers are not over-constrained.

## 11. Content expansion and layout

Check that:

- controls tolerate longer translations;
- text does not overlap or clip;
- fixed widths do not assume English length;
- buttons remain usable with expanded labels;
- responsive layouts support different line breaks;
- truncation does not hide essential meaning;
- typography supports the target scripts;
- screenshots or images do not contain untranslated essential text.

## 12. Locale state and persistence

Check that:

- locale state is consistent across server and client;
- SSR and hydration use the same locale;
- account preference, browser preference, route locale, and explicit choice have
  a defined precedence;
- locale switching refreshes dependent data and metadata;
- cached output varies by locale correctly;
- private data is not served in the wrong language due to cache collision.

## 13. Notifications and external communication

Check that:

- email, SMS, push, and exported documents use the intended locale;
- notification templates localise subject and body;
- dates and currencies remain consistent;
- fallback language is explicit;
- recipient locale does not leak from another user or tenant;
- links point to the equivalent locale.

# High-risk patterns

Pay particular attention to:

- string concatenation;
- hard-coded English plural rules;
- server/client locale mismatches;
- untranslated metadata;
- hard-coded left/right layout;
- locale-insensitive caching;
- IP redirects that trap users;
- user names and addresses forced into one cultural model;
- English-only validation patterns;
- missing font support for target scripts.

# Common false positives

Do not treat these as defects without product requirements:

- absence of locale switching in a single-locale product;
- use of one currency in a single-market product;
- untranslated developer-only logs;
- physical left/right where the meaning is genuinely physical;
- a locale-specific validation rule in a deliberately regional workflow;
- absence of `hreflang` on private or non-indexable pages.

# Output qualities

An internationalised implementation:

- separates content from code;
- supports grammatical variation;
- formats values by locale;
- preserves server/client consistency;
- supports relevant writing directions;
- localises metadata and communication;
- avoids cultural assumptions in data models;
- remains usable under text expansion.

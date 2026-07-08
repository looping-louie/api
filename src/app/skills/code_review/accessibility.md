---
id: accessibility
name: Accessibility
category: web_review
description: >
  Provides accessibility knowledge for semantic structure, keyboard interaction,
  focus management, forms, names and labels, visual presentation, motion, media,
  tables, authentication, and assistive-technology compatibility.
phase: review
artifacts:
    - prompt
    - current_artifact
    - git_diff
    - changed_files
output: json
---

# Accessibility

## Scope

This skill covers accessibility of websites, web applications, interfaces,
documents, and interactive workflows.

It applies to changes involving:

- page structure and landmarks;
- navigation and interactive controls;
- forms and validation;
- dialogs, menus, disclosures, tabs, and popovers;
- focus and keyboard behaviour;
- visual contrast, zoom, reflow, and motion;
- images, icons, audio, video, and data visualisation;
- tables and structured content;
- authentication and identity workflows;
- dynamic updates and asynchronous states.

Use the product's declared accessibility target and browser support policy as the
source of truth. In the absence of a project-specific target, use current WCAG
2.2 Level AA expectations for applicable web content.

# Technical checks

## 1. Semantic structure

Check that:

- the document has a valid language;
- landmarks expose header, navigation, main content, complementary content, and
  footer where appropriate;
- there is one primary `main` landmark;
- heading levels form a coherent hierarchy;
- headings describe sections rather than provide visual styling;
- lists use list markup;
- tables represent tabular data;
- buttons perform actions;
- anchors navigate;
- form controls use suitable native elements;
- interactive elements are not nested illegally.

Prefer native semantics before adding ARIA.

Avoid generic clickable containers when a native interactive element satisfies
the requirement.

## 2. Accessible names and descriptions

Check that:

- every control has an accessible name;
- icon-only buttons have explicit names;
- links communicate their destination or purpose;
- form controls have programmatically associated labels;
- groups of related controls have a group name;
- helper text and validation messages are associated with the relevant field;
- decorative images use empty alternative text;
- informative images have concise useful alternatives;
- complex visual content has an equivalent description where needed;
- visible labels and accessible names do not contradict each other.

Avoid placeholder-only labels.

## 3. Keyboard interaction

Check that:

- every interactive function works with a keyboard;
- focus order follows the logical reading and interaction order;
- custom controls implement the expected keyboard pattern;
- Enter and Space activation match native behaviour;
- arrow keys work where the control pattern requires them;
- Escape closes transient surfaces where expected;
- keyboard interaction does not trigger unrelated page shortcuts;
- shortcuts do not fire while the user types in editable content;
- no keyboard trap exists;
- positive `tabindex` is not used to repair incorrect DOM order.

Use roving `tabindex` only for composite widgets that require one tab stop.

## 4. Focus management

Check that:

- focus is visibly indicated;
- focus styling remains visible in hover, selected, invalid, disabled, and
  high-contrast states;
- opening a dialog or transient workflow moves focus intentionally;
- closing a transient surface restores focus to a sensible location;
- route or step changes place focus where users can understand the new context;
- hidden or inert content cannot receive focus;
- blocking dialogs make background content inert;
- programmatic focus does not unexpectedly interrupt reading or typing.

Do not remove focus outlines without an equally visible replacement.

## 5. Forms and validation

Check that:

- required fields are identified programmatically;
- input purpose uses suitable `type`, `autocomplete`, and `inputmode`;
- validation errors are textual;
- errors identify the affected field;
- dynamically added errors are announced where needed;
- error summaries link to fields when the form is long or complex;
- invalid input is preserved so the user can correct it;
- instructions do not rely only on colour, shape, position, or sound;
- password managers and paste are supported;
- authentication does not rely solely on cognitive puzzles;
- previously supplied information is not requested again without need.

## 6. Dynamic content and status

Check that:

- loading, success, error, and completion states are perceivable;
- live regions are used only when asynchronous updates require announcement;
- announcements are concise and not duplicated;
- progress indicators expose current value and total where applicable;
- disabled controls communicate why action is unavailable when necessary;
- optimistic updates do not conceal failure;
- time-limited interactions provide suitable control or extension.

Avoid announcing every minor visual update.

## 7. Visual presentation

Check that:

- text contrast meets the applicable threshold;
- meaningful non-text interface elements have sufficient contrast;
- information is not conveyed by colour alone;
- zoom and text resizing do not hide content or controls;
- content reflows without two-dimensional scrolling except where inherently
  necessary;
- fixed headers, overlays, and sticky elements do not obscure focused content;
- line height, spacing, and wrapping remain usable;
- selected, active, disabled, invalid, and success states remain distinguishable;
- forced-colours mode preserves meaning and operation.

## 8. Target size and pointer use

Check that:

- pointer targets meet the applicable WCAG 2.2 target-size requirement or have
  sufficient spacing;
- drag interactions have an accessible alternative;
- hover-only content can also be reached by keyboard and touch;
- pointer cancellation prevents accidental destructive activation;
- gestures do not require path-dependent movement without an alternative.

## 9. Motion and animation

Check that:

- non-essential motion respects `prefers-reduced-motion`;
- flashing content remains below seizure-risk thresholds;
- parallax, auto-scrolling, and movement can be reduced or disabled;
- animation does not block interaction;
- focus is not lost during transitions;
- essential state changes remain understandable without motion.

## 10. Dialogs and composite widgets

For dialogs, menus, tabs, listboxes, comboboxes, tree views, grids, and similar
widgets, check that:

- the chosen pattern matches the actual interaction;
- roles, states, and properties remain synchronised;
- keyboard behaviour matches the pattern;
- focus entry and exit are intentional;
- hidden panels are not exposed to assistive technology;
- selection and focus are not confused;
- native controls are used when they satisfy the requirement.

ARIA does not add behaviour. The implementation must provide the interaction
model.

## 11. Media and images

Check that:

- informative images have useful alternative text;
- decorative images are ignored by assistive technology;
- prerecorded video has captions;
- audio-only content has a transcript;
- audio description or equivalent information exists where visual content is
  essential;
- autoplay can be paused and does not start with unexpected sound;
- custom media controls are keyboard operable and named;
- charts expose the underlying data or a useful text summary.

## 12. Tables

Check that:

- tables are used only for data;
- the table has an accessible name where needed;
- header cells use correct scope or explicit relationships;
- captions and summaries explain complex structures;
- sortable headers expose current sort state;
- responsive presentation does not destroy header relationships;
- interactive controls inside tables remain reachable and understandable.

## 13. Language and reading order

Check that:

- the document language matches the primary content;
- inline language changes are marked;
- text direction matches the language and content;
- DOM order matches the intended reading order;
- CSS visual reordering does not create a contradictory keyboard or reading
  order;
- abbreviations and unusual terms have enough context.

## 14. Authentication and sensitive workflows

Check that:

- users can paste into password and verification fields;
- password managers can identify fields;
- one-time codes use suitable autocomplete values;
- authentication does not rely only on memory or transcription tasks;
- timeout warnings provide enough time to respond;
- errors do not reveal sensitive account existence unnecessarily;
- destructive or irreversible actions provide clear confirmation and recovery
  where appropriate.

## 15. Testing and evidence

Where project tooling exists, check that:

- automated accessibility checks cover changed pages and components;
- keyboard interaction is tested manually or through browser automation;
- screen-reader-sensitive widgets follow established patterns;
- contrast and forced-colours behaviour are verified;
- zoom and reflow are tested;
- dynamic announcements are not duplicated;
- accessibility regressions receive targeted tests.

Automated tools cannot establish full accessibility. They complement, rather
than replace, interaction testing.

# High-risk patterns

Pay particular attention to:

- inaccessible primary flows;
- unlabeled controls;
- clickable generic elements;
- dialogs without focus management;
- custom selection controls without keyboard support;
- validation communicated only by colour;
- hidden content remaining focusable;
- progress or status changes that are never announced;
- motion that ignores reduced-motion preferences;
- visual reordering that breaks reading order;
- overlays used as a substitute for accessible implementation.

# Common false positives

Do not treat these as defects without concrete impact:

- absence of ARIA where native semantics are sufficient;
- use of a custom component when it fully implements the correct pattern;
- absence of a live region for content that does not require announcement;
- absence of a skip link on a small page without repeated navigation;
- a decorative image with empty alternative text;
- a disabled control when the workflow clearly explains the prerequisite.

# References

This skill is based primarily on:

- Web Content Accessibility Guidelines 2.2;
- WAI-ARIA Authoring Practices;
- HTML accessibility guidance;
- established browser and assistive-technology behaviour.

Project-specific accessibility requirements take precedence when they are
stricter or more explicit.

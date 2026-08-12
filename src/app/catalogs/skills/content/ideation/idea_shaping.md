# Idea Shaping

## Scope

This skill covers the transformation of an early, incomplete, or ambiguous idea
into a coherent proposal that can be evaluated and later decomposed into
implementation work.

It applies when the input contains:

- a rough product or feature idea;
- an opportunity without a defined solution;
- a proposed solution without a clear problem;
- an oversized initiative that needs boundaries;
- competing solution directions;
- uncertainty about first-version scope;
- unresolved assumptions or dependencies.

The goal is not to create a complete specification. The goal is to produce
enough clarity for a team to decide whether the idea is worth pursuing and what
the smallest coherent version should achieve.

## Core shaping principles

### Start from the problem and desired change

A shaped idea must identify:

- who experiences the problem;
- what they are trying to accomplish;
- how they currently solve or avoid it;
- why the current situation is unsatisfactory;
- what observable outcome should improve.

Do not treat a requested feature as proof that the underlying problem is valid.

Separate:

- the user or customer problem;
- the desired outcome;
- the proposed solution.

A solution may change while the problem and outcome remain stable.

### Define the thesis

The thesis is a concise statement connecting:

- the target user or customer;
- the problem or opportunity;
- the proposed intervention;
- the expected outcome.

A useful thesis is specific enough to guide decisions but broad enough to allow
implementation alternatives.

Avoid theses that only restate a feature, such as "build a dashboard" or "add an
AI assistant."

### Establish appetite

Appetite defines how much time, cost, complexity, and organisational attention
the idea deserves.

It is not an estimate of how long an unconstrained solution might take.

Use appetite to decide:

- how small the first version must be;
- which trade-offs are acceptable;
- which risks require discovery before implementation;
- which quality attributes are mandatory;
- which capabilities must wait.

When appetite and proposed scope conflict, reduce or reshape the scope rather
than silently increasing the appetite.

### Shape the solution at the right level

Describe:

- the primary user journey;
- the central interaction or operating model;
- the minimum required capabilities;
- important system boundaries;
- expected inputs and outputs;
- decisions that materially affect feasibility.

Do not prematurely prescribe:

- every screen;
- every field;
- internal implementation details;
- exhaustive edge-case handling;
- visual polish beyond what the outcome requires.

The proposed solution should constrain the problem without preventing the
implementation team from making reasonable technical and design decisions.

### Define scope and non-goals

Scope must describe what the first coherent version includes.

Non-goals must state what is deliberately excluded.

Useful non-goals prevent:

- adjacent features from entering unnoticed;
- later reviewers from demanding unrelated completeness;
- implementation work from expanding around hypothetical future needs;
- temporary omissions from being mistaken for forgotten requirements.

A non-goal is not a hidden backlog. It is an explicit boundary for the current
idea.

### Identify risks and rabbit holes

A rabbit hole is an area that can consume disproportionate effort or introduce
uncertain dependencies.

Check for:

- unclear data availability or quality;
- unknown third-party API behaviour;
- authentication or permission complexity;
- migration and compatibility requirements;
- legal, privacy, security, or compliance constraints;
- operational ownership;
- performance or scale assumptions;
- cross-platform inconsistencies;
- ambiguous user states;
- integrations that require external approval;
- hidden content, localisation, or accessibility work;
- requirements that depend on future infrastructure.

Distinguish:

- known implementation work;
- assumptions that need validation;
- external dependencies;
- unresolved product decisions;
- risks that can invalidate the idea.

### Make validation explicit

Validation should target the highest-risk assumptions, not only general user
interest.

Define:

- what must be learned;
- which assumption it tests;
- the cheapest credible method;
- what result would support proceeding;
- what result would require reshaping or stopping.

Possible validation methods include:

- customer interviews;
- workflow observation;
- clickable prototypes;
- concierge delivery;
- technical spikes;
- data audits;
- pricing tests;
- limited pilots;
- instrumentation of an existing workflow.

Avoid validation activities that cannot change a decision.

### Define success criteria

Success criteria should describe observable evidence that the idea works.

Use a combination of:

- user behaviour;
- task completion;
- adoption or activation;
- quality or error reduction;
- time or cost reduction;
- commercial outcomes;
- operational reliability;
- qualitative evidence.

Avoid vanity metrics that can rise without demonstrating the desired outcome.

Success criteria do not need final numerical targets when evidence is
insufficient, but they must identify what will be measured.

## Shaping checks

Check that the shaped idea:

- states one coherent thesis;
- identifies a real user or customer;
- distinguishes the problem from the solution;
- defines the desired outcome;
- has an explicit appetite;
- proposes one understandable first-version experience;
- contains clear scope boundaries;
- contains meaningful non-goals;
- identifies critical assumptions and dependencies;
- includes a practical validation approach;
- defines observable success criteria;
- preserves unresolved decisions instead of inventing answers;
- remains concise enough to support a decision.

## Common failure patterns

### Solution-first framing

The artifact describes what to build but not why it matters.

Correction:

- restate the customer and problem;
- identify the desired change;
- treat the current solution as one hypothesis.

### Unbounded scope

The artifact combines a core idea with administration, analytics, integrations,
automation, migration, and future platform work.

Correction:

- choose one primary outcome;
- define the smallest coherent journey;
- move adjacent capabilities into non-goals.

### False certainty

The artifact presents assumptions as facts.

Correction:

- label assumptions;
- define validation;
- preserve open decisions.

### Excessive implementation detail

The artifact becomes a technical specification before the product shape is
settled.

Correction:

- retain only details that affect feasibility, cost, or user experience;
- defer implementation choices to planning.

### Vague validation

The artifact says "test with users" without identifying what must be learned.

Correction:

- connect each validation activity to a specific assumption and decision.

### Missing appetite

The artifact describes an ideal solution without any constraint on effort.

Correction:

- state the investment boundary;
- reduce scope until the proposal fits it.

## Output qualities

A well-shaped idea is:

- bounded;
- understandable;
- decision-ready;
- testable;
- explicit about uncertainty;
- concise;
- suitable as input to implementation planning.

It should enable a team to answer:

- Is this problem worth solving?
- Is this the right first version?
- What are we deliberately not doing?
- What could invalidate the proposal?
- What must we learn before committing further?

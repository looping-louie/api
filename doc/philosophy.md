# Looping Louie Philosophy

Looping Louie is not an agent builder.

It is a runtime for executing reproducible, review-driven LLM development workflows.

The project deliberately optimises for simplicity, reproducibility and
software engineering principles over autonomous behaviour.

---

## Core Principles

### Git is the source of truth

The repository is always the canonical representation of the project.

Looping Louie never stores an alternative project representation.

Every modification ultimately becomes a Git diff.

---

### Never modify the original repository during execution

Every harness execution happens inside an isolated Git worktree.

The original repository is modified only after every reviewer has approved the
final result.

Rejected iterations must leave the repository untouched.

---

### Git generates the diff

Generator models never generate git patches.

They describe filesystem operations.

The runtime applies those operations inside a worktree.

Git is responsible for computing the real diff.

Git is significantly more reliable than asking an LLM to produce patches directly.

---

### Small iterations

Each iteration should perform one logical improvement.

Small changes are:

- easier to review
- easier to understand
- cheaper to regenerate
- less destructive

Whenever possible, evolve the repository incrementally.

---

### One reviewer, one responsibility

Each reviewer should evaluate one concern only.

Examples:

- Code quality
- Nuxt conventions
- Accessibility
- Security
- SEO
- Performance
- UI preservation

Reviewers should not attempt to judge every aspect of the implementation.

Many focused reviewers produce better feedback than one general reviewer.

---

### Skills are reusable

A skill is a reusable review policy.

Skills should be independent from projects.

Projects compose skills.

Skills should never contain project-specific knowledge.

---

### The generator is disposable

The generator is simply the component that proposes changes.

It should be possible to replace it with another model without changing the runtime.

The runtime owns the workflow.

The model is just one implementation detail.

---

### Cheap generation, expensive validation

Generation should ideally be performed by inexpensive models.

Quality should come from multiple reviewers rather than an extremely expensive generator.

Improving validation is usually a better investment than improving generation.

---

### Prompt engineering belongs to the runtime

Business logic should never build prompts directly.

Prompt construction belongs in dedicated prompt builders.

This keeps prompts:

- testable
- versionable
- reusable
- provider independent

---

### Providers are interchangeable

Together, OpenAI, Anthropic, Gemini or future providers should expose the same
logical interface.

The runtime should depend on capabilities, not vendors.

---

### Reviews operate on diffs

Reviewers should receive only the information necessary to evaluate a change.

Normally this means:

- original task
- git diff
- changed file contents
- review skill

Entire repository snapshots are for generators, not reviewers.

---

### Preserve existing work

Unless explicitly requested, generated changes should extend existing
implementations rather than replacing them.

Large rewrites increase risk.

Incremental evolution is preferred.

---

### Fail safely

If something cannot be validated, it should not be merged.

When in doubt:

- reject
- explain why
- iterate again

Never guess.

---

### Deterministic execution

Every run should be reproducible.

The runtime should persist:

- prompts
- responses
- metrics
- diffs
- execution traces

This allows every execution to be inspected after completion.

---

### Observability first

Runs are first-class artefacts.

Every execution should leave enough information to answer questions such as:

- What changed?
- Why was it rejected?
- Which reviewer rejected it?
- Which prompt produced this result?
- How many tokens were consumed?
- How much did it cost?

---

### Architecture before optimisation

The simplest working architecture is preferred.

Optimisations should only be introduced after a clear bottleneck has been identified.

Avoid premature abstractions.

---

### Prefer boring technology

Use technologies that are:

- simple
- well understood
- maintainable
- production ready

Complexity should exist only when it creates measurable value.

---

### Small commits

Every approved task should become one commit.

Commits should represent logical units of work.

Large commits make review, rollback and debugging harder.

---

### Runtime over framework

Looping Louie is not tied to any language, framework or frontend stack.

Today it may generate Nuxt.

Tomorrow it may generate:

- FastAPI
- Django
- React
- Flutter
- Rust

The runtime should remain framework agnostic.

---

## Long-Term Vision

Looping Louie aims to become the execution runtime for production-grade LLM
software development.

The value is not generating code.

The value is producing software that is:

- reproducible
- reviewable
- observable
- incrementally improvable
- provider independent
- enterprise deployable

Generation is only the first step.

Quality is the product.

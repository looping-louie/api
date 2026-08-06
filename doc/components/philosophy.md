# Looping Louie Philosophy

Looping Louie is not an agent builder. It is a runtime for executing
reproducible, review-driven LLM development workflows.

The project deliberately optimizes for simplicity, reproducibility, and
software engineering principles over autonomous behavior.

## Core principles

### Git is the source of truth

The repository is always the canonical representation of the project. Looping
Louie never stores an alternative project representation. Every modification
ultimately becomes a Git diff.

### Never modify the original repository during execution

The API never mutates the target repository directly. Repository mutations
happen in the CLI under checkpoint guidance. The original repository is
modified only after every reviewer has approved the final result. Rejected
iterations must leave the repository untouched.

### Git generates the diff

Generator models never generate Git patches. They describe filesystem
operations. The CLI applies those operations in the local repository context,
and Git computes the real diff. Git is significantly more reliable than asking
an LLM to produce patches directly.

### Small iterations

Each iteration should perform one logical improvement. Small changes are easier
to review, understand, regenerate, and less destructive. Whenever possible,
evolve the repository incrementally.

### One reviewer, one responsibility

Each reviewer should evaluate one concern only. Examples include code quality,
Nuxt conventions, accessibility, security, SEO, performance, and UI
preservation. Reviewers should not attempt to judge every aspect of an
implementation. Many focused reviewers produce better feedback than one
general reviewer.

### Skills are reusable

A skill is a reusable review policy. Skills should be independent from projects;
projects compose skills. Skills should never contain project-specific
knowledge.

### The generator is disposable

The generator is simply the component that proposes changes. It should be
possible to replace it with another model without changing the runtime. The
runtime owns the workflow; the model is one implementation detail.

### Cheap generation, expensive validation

Generation should ideally use inexpensive models. Quality should come from
multiple reviewers rather than an extremely expensive generator. Improving
validation is usually a better investment than improving generation.

### Prompt engineering belongs to the runtime

Business logic should never build prompts directly. Prompt construction belongs
in dedicated prompt builders, keeping prompts testable, versionable, reusable,
and provider-independent.

### Providers are interchangeable

Together, OpenAI, Anthropic, Gemini, and future providers should expose the same
logical interface. The runtime should depend on capabilities, not vendors. See
[Providers](providers.md) for the current provider boundary.

### Reviews operate on diffs

Reviewers should receive only the information necessary to evaluate a change:

- original task;
- Git diff;
- changed file contents;
- review skill.

Entire repository snapshots are for generators, not reviewers.

### Preserve existing work

Unless explicitly requested, generated changes should extend existing
implementations rather than replace them. Large rewrites increase risk;
incremental evolution is preferred.

### Fail safely

If something cannot be validated, it should not be merged. When in doubt,
reject, explain why, and iterate again. Never guess.

### Deterministic execution

Every run should be reproducible. The runtime should persist prompts, responses,
metrics, diffs, and execution traces so every execution can be inspected after
completion.

### Observability first

Runs are first-class artefacts. Every execution should leave enough information
to answer what changed, why it was rejected, which reviewer rejected it, which
prompt produced it, how many tokens it consumed, and how much it cost.

### Architecture before optimisation

The simplest working architecture is preferred. Optimisations should only be
introduced after a clear bottleneck has been identified. Avoid premature
abstractions.

### Prefer boring technology

Use technologies that are simple, well understood, maintainable, and production
ready. Complexity should exist only when it creates measurable value.

### Small commits

Every approved task should become one commit. Commits should represent logical
units of work. Large commits make review, rollback, and debugging harder.

### Runtime over framework

Looping Louie is not tied to any language, framework, or frontend stack. Today it
may generate Nuxt; tomorrow it may generate FastAPI, Django, React, Flutter, or
Rust. The runtime should remain framework agnostic.

## Long-term vision

Looping Louie aims to become the execution runtime for production-grade LLM
software development.

The value is not generating code. The value is producing software that is
reproducible, reviewable, observable, incrementally improvable, provider
independent, and enterprise deployable.

Generation is only the first step. Quality is the product.

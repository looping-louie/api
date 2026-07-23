# Risk Analysis

## Scope

This skill covers risks that could prevent an idea, plan, implementation, or
operation from achieving its intended outcome.

It applies to:

- early product ideas;
- implementation plans;
- architecture decisions;
- integrations;
- launches;
- migrations;
- operational changes;
- enterprise deployments;
- commercial commitments.

Risk analysis should improve decisions, not create an exhaustive catalogue of
everything that could go wrong.

## Risk model

### Distinguish risks, issues, assumptions, and dependencies

- A **risk** is an uncertain event or condition that could affect the outcome.
- An **issue** is a problem already occurring.
- An **assumption** is an unverified belief used in the proposal.
- A **dependency** is something outside the work that must be available or
  completed.

Do not merge these categories. Each requires a different response.

### Describe each risk concretely

A useful risk statement contains:

- the uncertain event or condition;
- the cause or trigger;
- the affected objective;
- the likely impact.

Prefer:

> If the upstream API rate limit is lower than assumed, batch processing may
> miss the delivery window.

Avoid:

> API risk.

### Assess likelihood and impact

Use qualitative or numerical scales consistently.

Likelihood may consider:

- prior evidence;
- technical novelty;
- number of dependencies;
- external control;
- organisational experience;
- uncertainty in requirements.

Impact may affect:

- customer value;
- delivery time;
- cost;
- data integrity;
- security;
- privacy;
- compliance;
- revenue;
- reputation;
- operations;
- reversibility.

A low-likelihood catastrophic risk may deserve more attention than a
high-likelihood minor inconvenience.

### Assess detectability and timing

Consider:

- whether the risk will be visible before damage occurs;
- how quickly it can be detected;
- when it can first materialise;
- whether the team has time to respond;
- whether the effect is reversible.

Late-detected and irreversible risks deserve stronger controls.

## Risk categories

### Product risk

Check whether:

- the problem is important enough;
- the target customer is sufficiently specific;
- the proposed solution changes the desired outcome;
- the scope is coherent;
- adoption requires behaviour customers will not accept;
- success criteria measure real value;
- the proposal depends on unsupported assumptions.

### Technical risk

Check for:

- unknown feasibility;
- architecture mismatch;
- hidden complexity;
- unsupported platform behaviour;
- data quality or migration problems;
- performance or scale assumptions;
- compatibility constraints;
- third-party limitations;
- difficult reversibility;
- insufficient testability.

### Delivery risk

Check for:

- oversized tasks;
- unclear ownership;
- missing dependencies;
- unbounded discovery;
- simultaneous high-risk changes;
- external approvals;
- unrealistic sequencing;
- ambiguous acceptance criteria;
- critical work deferred until late.

### Operational risk

Check for:

- missing observability;
- unclear incident ownership;
- manual recovery;
- unsafe retries;
- single points of failure;
- capacity limits;
- secrets or configuration drift;
- unsupported deployment environments;
- incomplete rollback;
- fragile runbooks.

### Security and privacy risk

Check for:

- excessive trust in client input;
- exposed secrets;
- weak authorisation;
- cross-tenant access;
- data leakage;
- unsafe third-party transmission;
- unnecessary data collection;
- unclear retention;
- insecure defaults;
- abuse and denial-of-service surfaces.

### Legal and compliance risk

Check for:

- personal-data obligations;
- licensing restrictions;
- contractual commitments;
- sector requirements;
- accessibility obligations;
- retention and deletion duties;
- auditability gaps;
- geographic restrictions.

Do not assert legal conclusions without qualified evidence. Identify the need
for specialist review where appropriate.

### Commercial risk

Check for:

- unclear willingness to pay;
- acquisition cost;
- margin erosion;
- dependency on one customer or supplier;
- pricing complexity;
- support burden;
- contractual service levels;
- implementation cost exceeding appetite;
- value that cannot be demonstrated.

### Adoption and organisational risk

Check for:

- workflow disruption;
- training needs;
- unclear incentives;
- loss of control;
- stakeholder resistance;
- migration burden;
- missing executive support;
- changes that benefit buyers but burden users;
- governance or procurement barriers.

## Risk treatment

For material risks, choose an explicit treatment:

- **Avoid:** change the proposal so the risk no longer exists.
- **Reduce:** lower likelihood or impact through design or controls.
- **Transfer:** assign exposure contractually or through insurance or a service.
- **Accept:** proceed knowingly because treatment costs more than the exposure.
- **Investigate:** run discovery before committing.

A treatment should identify:

- owner;
- action;
- timing;
- evidence of completion;
- residual risk.

### Risk-driven validation

Prioritise validation by expected decision value.

Use:

- prototypes for usability or workflow risk;
- technical spikes for feasibility risk;
- load tests for capacity risk;
- data audits for migration risk;
- threat modelling for security risk;
- customer interviews or pilots for adoption risk;
- contract review for legal or commercial risk;
- operational exercises for recovery risk.

Do not build the complete solution merely to validate one assumption.

## Challenge checks

Check that the proposal:

- names its critical assumptions;
- distinguishes blockers from manageable risks;
- addresses the highest-impact risks early;
- has a fallback or rollback for irreversible changes;
- does not hide risk inside vague future work;
- does not depend on all optimistic assumptions being true;
- remains within appetite after mitigation;
- assigns ownership for material operational risks;
- preserves unresolved uncertainty visibly.

## Common failure patterns

### Generic risk lists

Correction:

- connect every risk to a specific objective and failure mechanism.

### Treating all risks equally

Correction:

- prioritise by likelihood, impact, detectability, timing, and reversibility.

### Mitigation without ownership

Correction:

- identify who acts, when, and how completion is verified.

### Risks converted into scope creep

Correction:

- distinguish necessary controls from speculative future-proofing.

### Assumptions presented as mitigated

Correction:

- require evidence or explicit acceptance.

### No residual risk

Correction:

- state what remains after treatment.

## Output qualities

A useful risk analysis is:

- specific;
- prioritised;
- decision-oriented;
- proportional to the proposal;
- explicit about uncertainty;
- connected to treatments and validation;
- concise enough to guide action.

It should make clear which risks can be accepted, which require mitigation, and
which must be resolved before proceeding.

<!--
SYNC IMPACT REPORT
==================
Version change: 1.0.0 → 1.1.0
Bump rationale: Added Deployment Tiers section (MINOR — material expansion; new
section relaxes Principles III and V for Prototype/Learning tier; no principle
removed or redefined).

Amendment 1.1.0 — Deployment Tiers:
- Added "Deployment Tiers" section defining Prototype/Learning and Production tiers.
- Prototype/Learning tier: SonarQube CI not required (compensated by local
  flake8/pylint/bandit); select_for_update() not required with SQLite3 backend
  (@transaction.atomic suffices).
- All NON-NEGOTIABLE principles (I Security, II Test-First) and Principles IV
  and V (non-locking parts) remain fully in force in both tiers.
- Active tier MUST be declared in project plan.md.

Prior history:
- 1.0.0: Initial ratification.

Templates reviewed for consistency:
- ✅ .specify/templates/plan-template.md — Constitution Check gate now includes
     tier declaration. No structural change required.
- ✅ .specify/templates/spec-template.md — no change required.
- ⚠ .specify/templates/tasks-template.md — PENDING (from 1.0.0): Principle II
     (Test-First, NON-NEGOTIABLE) conflicts with template's "Tests are OPTIONAL"
     stance. Still unresolved.

Follow-up TODOs:
- Reconcile the tasks-template.md test-optionality conflict noted above.
- Any project operating in Prototype/Learning tier MUST include a Production
  migration TODO in its roadmap before involving real users or real money.
-->

# Banking App Constitution

## Core Principles

### I. Security & Confidentiality First (NON-NEGOTIABLE)

The application handles money, credentials, and personally identifiable information;
security is the highest-priority constraint and overrides convenience or speed.

- All data MUST be encrypted in transit (TLS 1.2 or higher) and at rest.
- Secrets (database credentials, API keys, signing keys) MUST be stored outside
  source control in environment variables or a managed secret store, and MUST NEVER
  be committed to the repository.
- Django security protections MUST be enabled in every deployed environment: CSRF
  protection, `SECURE_SSL_REDIRECT`, HTTP Strict Transport Security, secure and
  HTTP-only session and CSRF cookies, and clickjacking and XSS middleware.
- Authentication MUST require multi-factor authentication for staff and privileged
  accounts; passwords MUST be stored using Django's strong password hashers.
- Authorization MUST follow least privilege: every endpoint and action verifies the
  acting user's permission to the specific resource.
- The OWASP Top 10 MUST be mitigated; SonarQube security hotspots MUST be reviewed
  and resolved before merge.

**Rationale**: A single breach in a banking application is financially and legally
catastrophic and irreversible for affected customers.

### II. Test-First Development (NON-NEGOTIABLE)

Tests are written before implementation. The correctness of financial logic is
proven, not assumed.

- The cycle MUST be: write tests → confirm they fail → implement → confirm they
  pass → refactor (Red-Green-Refactor).
- Every money-handling code path MUST have both unit tests and integration tests.
- New code MUST meet the coverage threshold defined in Principle III; merges that
  drop coverage below that threshold MUST be blocked.
- Bug fixes MUST begin with a failing test that reproduces the defect.

**Rationale**: An incorrect calculation or an unguarded path can silently move real
money; tests are the safety net that makes correctness verifiable.

### III. Code Quality Gates (SonarQube)

SonarQube is the objective, automated arbiter of code quality, and its Quality Gate
is a mandatory merge gate.

- Every pull request and every commit to the main branch MUST be analyzed by
  SonarQube, and the Quality Gate MUST pass before merge.
- The Quality Gate MUST enforce, on new code, the project's chosen defaults: zero
  new bugs, zero new vulnerabilities, all new security hotspots reviewed, test
  coverage of at least 80%, duplicated lines of at most 3%, and reliability,
  security, and maintainability ratings of A. These thresholds MAY be changed only
  through the amendment process defined in Governance.
- Blocker and Critical issues MUST be fixed before merge; they MUST NOT be deferred
  or marked "won't fix" without recorded maintainer approval.
- A failing Quality Gate MUST block the CI pipeline.

**Rationale**: Manual review alone misses regressions; an automated gate enforces a
consistent quality floor on every change.

### IV. Auditability & Observability

Every action that touches money or security MUST be reconstructable after the fact.

- Each financial transaction and security-relevant event (authentication,
  permission change, fund transfer, account mutation) MUST produce an immutable,
  timestamped audit record that attributes the acting user or system.
- Application logs MUST be structured (machine-parseable) and MUST carry a
  correlation or request identifier that links related events.
- Sensitive data — full card numbers, passwords, authentication tokens, and raw
  personally identifiable information — MUST NEVER appear in logs, error messages,
  or analytics events.
- Audit records and logs MUST be retained for the period required by applicable
  regulation and MUST be protected against tampering and unauthorized deletion.

**Rationale**: Regulators, auditors, and incident responders require a complete and
tamper-evident record of who did what and when.

### V. Data Integrity & Transactional Consistency

Money is never created, destroyed, or duplicated by a software defect.

- Every operation that moves or modifies funds MUST be atomic: wrapped in a database
  transaction so it either fully succeeds or fully rolls back.
- Operations with concurrent access to the same balance MUST use row-level locking
  (for example, `select_for_update`) to prevent race conditions.
- Monetary values MUST use a fixed-precision decimal type; floating-point types MUST
  NOT be used to represent money.
- Externally triggered operations (API calls, webhooks, payment callbacks) MUST be
  idempotent so that retries cannot double-apply an effect.
- Database migrations MUST be reviewed, MUST be reversible where feasible, and MUST
  NOT cause unintended data loss.
- Account balances MUST always reconcile against the recorded transaction history.

**Rationale**: A race condition or rounding error that corrupts a balance directly
harms customers and breaks trust in the institution.

## Technology & Compliance Standards

- **Backend framework**: Django on a currently supported release (LTS preferred),
  running on Python 3.11 or higher.
- **Data layer**: The Django ORM with a transactional relational database
  (PostgreSQL recommended); any raw SQL MUST be parameterized.
- **Dependencies**: All dependencies MUST be version-pinned. Dependency
  vulnerability scanning MUST run in CI, and known high-severity vulnerabilities
  MUST be remediated before release.
- **Static analysis**: SonarQube MUST be integrated into CI for every pull request
  and for the main branch, in accordance with Principle III.
- **Regulatory compliance**: The application MUST comply with PCI DSS for any
  cardholder data and with applicable data-protection law for personal data.
- **Environment isolation**: Development, staging, and production MUST be separate
  environments. Production data MUST NOT be copied into lower environments unless it
  is masked or anonymized.

## Development Workflow & Quality Gates

- All changes MUST be made through pull requests; direct pushes to the main branch
  MUST be disabled.
- Every pull request MUST receive at least one approving review. Changes to
  security-sensitive or money-moving code MUST receive at least two approving
  reviews.
- A pull request MUST NOT be merged until all automated tests pass, the SonarQube
  Quality Gate passes, and every security hotspot it introduces has been reviewed.
- The "Constitution Check" gate in the implementation plan MUST pass before
  implementation begins; unavoidable violations MUST be recorded with justification
  in the plan's Complexity Tracking section.
- Production deployments MUST require a passing CI pipeline and explicit release
  approval from a maintainer.

## Deployment Tiers

Projects using this constitution MUST declare their active tier in `plan.md`.

### Prototype / Learning Tier

For exploratory or educational projects where operational infrastructure is
intentionally minimal. The following relaxations apply:

- **Principle III (SonarQube)**: SonarQube CI integration is not required.
  Compensating controls MUST be applied: `flake8`, `pylint`, and `bandit` must
  run locally and pass before each commit. The project MUST document this
  deviation in Complexity Tracking.
- **Principle V (`select_for_update`)**: Row-level locking via
  `select_for_update()` is not required when using SQLite3 as the database
  backend. All balance-modifying operations MUST still be wrapped in
  `@transaction.atomic`, which in SQLite3 issues an exclusive write lock that
  prevents concurrent corruption. The project MUST document this deviation in
  Complexity Tracking.

All other principles — including the NON-NEGOTIABLE principles (I and II),
Principle IV, and all non-locking requirements of Principle V — remain fully in
force regardless of tier.

A roadmap TODO to migrate to the Production tier MUST be included in the project
plan before any real users or real money are involved.

### Production Tier

All five principles apply fully and without exception. PostgreSQL (or equivalent)
is required. SonarQube Quality Gate is a mandatory merge gate.

## Governance

- This constitution supersedes all other development practices. Where a practice
  conflicts with this constitution, the constitution prevails.
- Amendments MUST be proposed through a pull request that documents the change, its
  rationale, and its impact, and MUST be approved by the project maintainers before
  taking effect.
- Versioning of this constitution follows semantic versioning:
  - **MAJOR**: backward-incompatible governance changes, or the removal or
    redefinition of a principle.
  - **MINOR**: a new principle or section is added, or guidance is materially
    expanded.
  - **PATCH**: clarifications, wording fixes, and non-semantic refinements.
- Every pull request and review MUST verify compliance with this constitution.
  Violations MUST be remediated or recorded with an approved, documented
  justification.
- Runtime development guidance for contributors and AI agents is maintained in
  `CLAUDE.md` at the repository root and MUST stay consistent with this
  constitution.

**Version**: 1.1.0 | **Ratified**: 2026-05-21 | **Last Amended**: 2026-05-21

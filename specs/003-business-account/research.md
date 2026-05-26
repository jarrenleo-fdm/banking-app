# Research: Business Account (Revised Model)

## Technology Stack

**Decision**: Extend the existing Django 5.x / Python 3.14.5 / SQLite3 (prototype tier) stack — no
new dependencies required.

**Rationale**: All required primitives (models, forms, services, views, templates) are already
present. The mock-SQL creation pattern is a service function wrapped in `@transaction.atomic`,
which Django already provides.

**Alternatives considered**: Django REST Framework for a JSON API — rejected; the app is
server-rendered with no existing API layer.

---

## Decision 1 — BusinessAccount as a standalone model (not tied to CustomUser)

**Decision**: `BusinessAccount` is a new top-level model with its own `balance` field. It is not
a `User` and has no login session of its own.

**Rationale**: The spec explicitly states the business account is not a login account. Attaching
it to `CustomUser` (via `account_type`) was the original design error. A standalone model cleanly
expresses that the business entity is managed *by* users, not *as* a user.

**Alternatives considered**:
- Reuse `Account` with `account_type=BUSINESS` (old model) — rejected; it conflates authentication
  identity with the banking entity.
- Use Django's generic content type framework — rejected; over-engineered for a demo.

---

## Decision 2 — Separate BusinessTransaction model (not extending Transaction)

**Decision**: A new `BusinessTransaction` model records all executed/rejected transactions for a
`BusinessAccount`. It mirrors the `Transaction` field set but FKs to `BusinessAccount` instead of
`Account`.

**Rationale**: Making `Transaction.account` nullable to accommodate both personal and business
accounts would break every queryset in the personal account flow and violate the "surgical changes"
principle. Two clean models are simpler than one model with dual nullable FKs.

**Alternatives considered**:
- Nullable `business_account` FK on existing `Transaction` — rejected; breaks non-null assumption
  throughout the codebase.
- Generic FK (ContentType) — rejected; unnecessary abstraction for a prototype.

---

## Decision 3 — Modify existing Authoriser model (not a new parallel model)

**Decision**: Change `Authoriser.business_account` FK target from `Account` → `BusinessAccount`
and promote it from `ForeignKey` to `OneToOneField` in a single migration.

**Rationale**: Creating a `BusinessAuthoriser` model alongside the old `Authoriser` would leave
dead code and a confused schema. One clean migration replaces the wrong relationship.

**Alternatives considered**:
- New `BusinessAuthoriser` model in parallel — rejected; creates schema junk and requires all
  authoriser views to import both models.

---

## Decision 4 — Sequential counter for demo phone numbers

**Decision**: Manager users get the next odd number in the `8xxxxxxx` range (80000001, 80000003, …);
authoriser users get the next even number (80000002, 80000004, …). The service queries existing
phone numbers before each assignment.

**Rationale**: `CustomUser.phone_number` must be unique and match `^[89]\d{7}$`. A counter is
deterministic, clearly demo data, and provably unique within the query.

**Alternatives considered**:
- Hash of business name truncated to 8 digits — rejected; collision risk and hard to reason about.
- Fixed hardcoded values — rejected; breaks after the first business account is created.

---

## Decision 5 — Minimum balance floor (7,000) enforcement

**Decision**: Enforced at two points:
1. **Account creation**: `initial_deposit < Decimal("7000.00")` raises `BankingError`. Form-level `min_value=Decimal("7000.00")` is the first defence; service guard is the second.
2. **Account manager submission** (`create_pending_*`): guard `balance - amount < Decimal("7000.00")` raises `InsufficientFundsError`. No pending transaction is created.
3. **Authoriser approval** (`approve_business_pending`): if `balance - amount < Decimal("7000.00")`, auto-reject — delegate to reject path (records `BusinessTransaction(REJECTED)`, sets `PendingTransaction.status = REJECTED`), return `False`.

**Rationale**: Spec FR-012 + FR-013 explicitly require enforcement at both submission and approval. Auto-rejection at approval handles race conditions (e.g. balance changed between submission and approval due to another approved transaction). Returning `bool` (not raising) at approval because auto-rejection is a defined business outcome, not an error.  
**Alternatives considered**: Enforce only at submission — rejected; spec mandates both. Raise exception on auto-rejection — rejected; auto-rejection is a normal success path (FR-013).

---

## Decision 6 — Initial deposit recorded as BusinessTransaction

**Decision**: `BusinessTransaction.objects.create(transaction_type=DEPOSIT, amount=initial_deposit, balance_after=initial_deposit)` is created inside the same `@transaction.atomic` block as account creation.  
**Rationale**: FR-014 — initial deposit must appear in business account transaction history.  
**Alternatives considered**: Record in a separate step — rejected; must be atomic with account creation.

---

## Decision 8 — No saved billers for business accounts

**Decision**: Business account bill payments submit biller category, reference, and amount inline
each time. The `Biller` model is not extended.

**Rationale**: Extending `Biller` with a nullable `business_account` FK would break its
`unique_together` constraint and require migrations touching personal account flows. For a demo,
inline bill payments are sufficient.

**Alternatives considered**:
- Add `business_account` nullable FK to `Biller` — rejected; requires constraint changes and
  complicates the personal biller flow.
- Separate `BusinessBiller` model — rejected; over-engineered for demo scope.

---

## Decision 9 — Credential generation pattern

**Decision**: Passwords are generated as `"Demo@" + 6 random chars` (letters + digits + `@#!`),
satisfying the app's `PasswordComplexityValidator`. Usernames follow `manager.<slug>` /
`authoriser.<slug>` where `<slug>` is the business name lowercased, non-alphanumeric chars
stripped, truncated to 20 chars. A numeric suffix resolves collisions.

**Rationale**: Generated passwords must pass Django's built-in validators (min length, complexity)
and the app's custom `PasswordComplexityValidator` (defined in `accounts/validators.py`).
The `Demo@` prefix satisfies uppercase + special-char requirements while being obviously demo data.

**Alternatives considered**:
- UUID-based passwords — rejected; may fail complexity validators and are harder to read on screen.
- Fixed demo password for all accounts — rejected; security principle (Principle I) requires
  distinct credentials.

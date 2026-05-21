# Research: Billing System

## Summary

No external unknowns require resolution — the full tech stack is established by the constitution and existing codebase. All decisions below are confirmed against the running project.

---

## Decision 1: App placement — new app vs. extend `banking`

**Decision**: Extend the existing `banking` app. No new Django app is created.

**Rationale**: Billers and bill payments are a direct extension of the money-movement domain already owned by `banking`. Adding a new app for a single pair of models and a handful of views introduces unnecessary indirection (extra `INSTALLED_APPS` entry, cross-app imports, duplicated URL namespace setup) with no architectural benefit at this scale.

**Alternatives considered**:
- New `billing` Django app — rejected; over-engineered for the feature scope and the project's Prototype tier.

---

## Decision 2: Bill payment transaction representation

**Decision**: Add a `BILL_PAYMENT` transaction type to the existing `Transaction` model and store the biller's name in `Transaction.description` at payment time.

**Rationale**: `Transaction` is already the immutable audit log for all balance changes. Reusing it for bill payments means bill payments automatically appear in the transaction history (satisfying FR-009) without a second query or a new model. Storing the biller name in `description` at payment time ensures the audit record is self-contained — deleting the `Biller` row later does not break history (satisfying the "deleting a biller retains history" assumption).

**Alternatives considered**:
- Separate `BillPayment` model with a FK to both `Biller` and `Transaction` — rejected; adds a join and a nullable FK that complicates history queries. Not needed at this scale.
- Store a FK from `Transaction` to `Biller` — rejected; `Transaction` is intended to be immutable and self-describing; a SET_NULL FK would silently degrade historical records on biller deletion.

---

## Decision 3: Biller ownership and isolation

**Decision**: `Biller` has a FK to `Account` (not to `User` directly), consistent with how the rest of the data model is structured.

**Rationale**: The existing models use `Account` as the financial entity. Linking `Biller` to `Account` keeps the ownership model consistent and makes access-control queries identical to existing patterns (`request.user.account.billers`).

---

## Decision 5: Biller name — free-text vs. predefined categories

**Decision**: `Biller.name` is constrained to a fixed set of five predefined categories stored as Django model choices: `Electricity`, `Water & Utilities`, `Internet & Broadband`, `Telecommunications`, `Town Council / Maintenance`.

**Rationale**: Predefined categories eliminate typos, enable consistent display labels, and make the payment history immediately recognisable. Django's `CharField(choices=...)` enforces the constraint at the model level with no schema change (the underlying column remains a `VARCHAR`). `BillerForm.name` becomes a `ChoiceField` which renders as a `<select>` dropdown automatically.

**Alternatives considered**:
- Free-text `CharField` — original design; rejected after clarification (error-prone, inconsistent history labels).
- Separate `BillerCategory` model with FK — rejected; overkill for a fixed, non-user-editable list of five values that will not change at runtime.

---

## Decision 6: Tier declaration

**Decision**: Prototype / Learning tier (as already established by the project's SQLite3 backend).

**Rationale**: The project uses SQLite3 and does not have SonarQube CI. The constitution's Prototype tier compensating controls apply: `flake8`, `pylint`, and `bandit` run locally; `@transaction.atomic` replaces `select_for_update()`.

# Research: Business Account Registration

## Existing Codebase Findings

### Decision: account_type stored on Account model (not CustomUser)

- **Rationale**: `CustomUser` is a pure authentication model (username, email, phone_number, password). `Account` is the banking entity and the correct home for financial account classification. Adding `account_type` to `Account` keeps the auth model free of domain concerns and aligns with the existing separation: `accounts` app = auth, `banking` app = banking operations.
- **Alternatives considered**: Adding `account_type` to `CustomUser` — rejected; mixes auth and domain concerns. Introducing a separate `AccountType` table — rejected; a single CharField with choices is sufficient for a two-value enum at this scope.

### Decision: BusinessProfile model in banking app, linked OneToOne to Account

- **Rationale**: Business-specific data (company name, registration number) is a banking-domain concern, not an auth concern. Linking `BusinessProfile` directly to `Account` via `OneToOne` means all business context is reachable from `account.business_profile` without crossing app boundaries unnecessarily. The `Account` model already has the OneToOne relationship with `CustomUser`, so both are accessible from a single starting point.
- **Alternatives considered**: Linking `BusinessProfile` to `CustomUser` (in the `accounts` app) — rejected; business registration data belongs in the banking domain. A separate `accounts` sub-table — rejected; adds cross-app FK complexity with no benefit.

### Decision: account_type and BusinessProfile set in signup_view after signal

- **Rationale**: `Account` is auto-created by the `post_save` signal on `CustomUser` with `account_type=PERSONAL` as default. The signup view already handles post-signal work (setting `initial_balance`). Following the same pattern: after `form.save()`, fetch `user.account`, update `account_type` with `save(update_fields=["account_type"])`, and — if business — create `BusinessProfile`. This is safe because signal and view run sequentially in the same request thread.
- **Alternatives considered**: Modifying the signal to accept account_type — rejected; signals do not carry form data cleanly. Creating Account directly in the view — rejected; would duplicate the signal logic and break other registration paths.

### Decision: business_registration_number format — alphanumeric, 6–20 characters

- **Rationale**: The spec states no specific country standard is required. A `RegexValidator(r'^[A-Za-z0-9]{6,20}$')` covers government-issued alphanumeric registration numbers (Singapore UEN: 9–10 chars, UK Companies House: 8 chars, US EIN: 10 digits). The range 6–20 is permissive enough for all common formats.
- **Alternatives considered**: Country-specific format — out of scope (spec assumption). UUID-style format — not consistent with real registration number conventions.

### Decision: Prototype / Learning Tier (inherited from project baseline)

- **Rationale**: Project uses SQLite3 and `@transaction.atomic` without `select_for_update()`. SonarQube CI is not configured. This feature does not change the tier; it inherits the existing Prototype/Learning tier configuration.
- **Alternatives considered**: N/A — tier is set at project level.

### Decision: Business field visibility toggled with inline JavaScript

- **Rationale**: The project has no JS build pipeline; all existing interactivity (password criteria checklist, UX enhancements) uses inline or single static JS files. A small inline `<script>` block that shows/hides the business fields div on radio button change is sufficient and adds no dependency.
- **Alternatives considered**: Server-side conditional rendering only (two separate form pages) — rejected; creates an unnecessary extra step for the user. A JavaScript framework — rejected; not present in the project.

### Decision: Migration is additive and reversible

- **Rationale**: Adding `account_type` with a default of `PERSONAL` is non-breaking for existing rows. `BusinessProfile` is a new table with no impact on existing data. Django's migration framework will generate a clean, reversible migration.
- **Alternatives considered**: Data migration to backfill account_type — not needed; `default=PERSONAL` handles existing rows automatically.

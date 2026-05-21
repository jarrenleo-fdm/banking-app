# Research: Core Banking Operations

Generated: 2026-05-21 | Branch: `001-core-banking-operations`

All "NEEDS CLARIFICATION" items from Technical Context are resolved below.

---

## 1. Framework & Database

**Decision**: Django 5.2 LTS on Python 3.11+; SQLite3 via Django ORM
**Rationale**: User-specified; LTS aligns with constitution; zero-configuration
database appropriate for Prototype/Learning tier
**Alternatives considered**: Django 4.2 LTS (still supported, older); PostgreSQL
(constitution recommendation for Production tier — deferred)

Key configuration decisions:
- `django-environ` for `.env` parsing (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`,
  email settings — never hardcoded)
- Security middleware enabled in all environments: `SecurityMiddleware`,
  `XFrameOptionsMiddleware`, `CsrfViewMiddleware`
- `X_FRAME_OPTIONS = 'DENY'`, `SECURE_CONTENT_TYPE_NOSNIFF = True`
- `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` deferred
  to production (flag in Production Migration TODO in plan.md)

---

## 2. SQLite3 Concurrency & Data Integrity

**Decision**: Wrap all balance-modifying operations in `@transaction.atomic`;
omit `select_for_update()` (raises `NotSupportedError` on SQLite3 backend)
**Rationale**: SQLite3 issues `BEGIN EXCLUSIVE` inside `@transaction.atomic`,
blocking any concurrent writer until commit or rollback. At prototype scale on a
single server this provides equivalent protection to row-level locking.
**Constitution tier**: Prototype/Learning — deviation recorded per constitution
v1.1.0 §Deployment Tiers
**Migration path to PostgreSQL**: Add `Account.objects.select_for_update().get()`
inside each atomic block in `banking/services.py`. No model or URL changes
required.

---

## 3. Phone Number Format

**Decision**: 8-digit national format; first digit must be 8 or 9;
regex `^[89]\d{7}$`; stored as normalized digits-only string
**Rationale**: User specification; matches Singapore mobile number convention;
consistent with spec's single-country assumption
**Normalization**: Strip all whitespace and hyphens before validation; store
only the 8 canonical digits
**Implementation**: `RegexValidator(r'^[89]\d{7}$')` on model field;
normalization in form `clean_phone_number()` (strip + remove hyphens before
validator runs)
**Used for**: Registration uniqueness (FR-028); transfer recipient lookup
(FR-015); displayed on dashboard as the user's own number

---

## 4. Credential Security

### Passwords

**Decision**: Django Argon2 hasher as first entry in `PASSWORD_HASHERS`
**Rationale**: Memory-hard; resistant to GPU/ASIC brute force; constitution
requires "Django's strong password hashers" (Principle I)
**Configuration**:
```python
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",  # fallback for existing hashes
]
```
**Package**: `django[argon2]` (installs `argon2-cffi`)

### Usernames

**Decision**: Store in original casing; enforce case-insensitive uniqueness via
`UniqueConstraint(Lower('username'), name='unique_username_case_insensitive')`
(Django 4.0+ functional unique index); login uses `username__iexact` lookup
**Rationale**: Usernames are identifiers, not secrets. Hashing was considered
but rejected: HMAC-based hashing with `SECRET_KEY` creates irrecoverable state
if the key rotates, and Argon2 hashing (with random salt) makes lookup
impossible. Functional unique constraint achieves the spec's case-insensitivity
requirement without added risk.
**Login uniqueness guarantee**: `User.objects.get(username__iexact=input)` raises
`User.DoesNotExist` on no match or `MultipleObjectsReturned` on collision
(impossible given unique constraint — query safely)

---

## 5. Money Representation

**Decision**: `DecimalField(max_digits=12, decimal_places=2)` for all monetary
fields (balance, transaction amounts); Python `Decimal` for all arithmetic
**Rationale**: Exact representation; no floating-point errors; constitution
mandates fixed-precision decimal (Principle V)
**Invariants enforced in service layer**:
- `amount > Decimal('0.00')` for every operation (FR-014, FR-020)
- `account.balance >= Decimal('0.00')` after every operation (FR-013, FR-017)

---

## 6. Password Reset

**Decision**: Django's built-in `PasswordResetView` and `PasswordResetConfirmView`
with custom email templates
**Rationale**: HMAC-based token (keyed by `last_login` timestamp + user PK);
token is automatically invalidated after use; no additional DB model required;
battle-tested implementation
**Token lifetime**: `PASSWORD_RESET_TIMEOUT = 3600` (1 hour; FR-031)
**Security**: `PasswordResetView` always returns the same response regardless
of whether the email exists — satisfies FR-029
**Email backend**: Console backend in development (`EMAIL_BACKEND` in `.env`);
SMTP via env vars in production
**Alternatives considered**: Custom token model (unnecessary; worse security
than Django's HMAC approach; extra code surface)

---

## 7. Testing Strategy

**Decision**: `pytest-django`; Red-Green-Refactor; unit + integration tests
mandatory for all money-handling paths
**Organization**:
- `accounts/tests/test_models.py` — CustomUser uniqueness, phone validation
- `accounts/tests/test_views.py` — registration, login, password reset flows
- `banking/tests/test_models.py` — Account, Transaction field constraints
- `banking/tests/test_services.py` — deposit, withdraw, transfer logic (pure
  unit tests with DB, covering all acceptance scenarios from spec)
- `banking/tests/test_views.py` — dashboard, deposit/withdraw/transfer views
**Coverage target**: 80% (Principle III — applies in all tiers)
**Test data**: `factory_boy` factories in `tests/factories.py` per app
**Alternatives considered**: Django's `TestCase` (compatible; `pytest-django`
preferred for fixtures and parametrize support)

---

## 8. Static Analysis (Prototype Tier Compensating Controls)

**Decision**: `flake8`, `pylint`, `bandit` via `pre-commit` hooks on every commit
**Rationale**: Constitution v1.1.0 Prototype tier requires compensating controls
in place of SonarQube CI
**Configuration**: `.pre-commit-config.yaml` at repo root
**Scope**: All Python files in `accounts/`, `banking/`, `banking_app/`

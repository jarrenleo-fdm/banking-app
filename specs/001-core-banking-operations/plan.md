# Implementation Plan: Core Banking Operations

**Branch**: `001-core-banking-operations` | **Date**: 2026-05-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-core-banking-operations/spec.md`

**Active Tier**: Prototype / Learning (constitution v1.1.0 §Deployment Tiers)

## Summary

Build a Django 5.2 web application backed by SQLite3 delivering core banking
operations: user registration and authentication with Argon2-hashed passwords,
a balance dashboard, deposits and withdrawals, peer-to-peer transfers identified
by an 8-digit phone number (first digit 8 or 9), and an immutable transaction
history. All monetary operations are atomic and overdraft-protected.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Django 5.2 LTS, argon2-cffi (`django[argon2]`),
django-environ, pytest-django, factory-boy, flake8, pylint, bandit, pre-commit
**Storage**: SQLite3 via Django ORM (`db.sqlite3`; zero-configuration for
prototype tier)
**Testing**: pytest-django; Red-Green-Refactor cycle; unit + integration tests
mandatory for all money-handling paths; 80% coverage target
**Target Platform**: Local development / single-server; served via Django dev
server in development, Gunicorn + Nginx in production
**Project Type**: Web application (Django MTV; server-rendered HTML templates)
**Performance Goals**: < 500 ms response time for all banking operations under
light load
**Constraints**: Single currency; phone numbers 8 digits starting with 8 or 9;
no external payment integrations; no account deletion; no MFA for customers (out
of scope per spec); password reset via email
**Scale/Scope**: Prototype / learning project; small user base; single database
instance

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I | Security & Confidentiality First (NON-NEGOTIABLE) | ✅ PASS | Argon2 password hashing; Django security middleware enabled; secrets via env vars; CSRF/session cookie security; generic auth error messages |
| II | Test-First Development (NON-NEGOTIABLE) | ✅ PASS | Red-Green-Refactor cycle enforced; all money-handling paths require unit + integration tests |
| III | Code Quality Gates (SonarQube) | ⚠ PROTOTYPE TIER | SonarQube CI deferred (Prototype/Learning tier); compensating controls: flake8, pylint, bandit via pre-commit hooks. See Complexity Tracking. |
| IV | Auditability & Observability | ✅ PASS | Structured Django logging; Transaction model is immutable audit trail; no sensitive data in logs |
| V | Data Integrity & Transactional Consistency | ⚠ PROTOTYPE TIER | `select_for_update()` unsupported on SQLite3; `@transaction.atomic` with SQLite exclusive write-lock used instead. DecimalField for all monetary values. See Complexity Tracking. |

**Gate result**: PROCEED — two Prototype-tier deviations documented in
Complexity Tracking below; constitution v1.1.0 explicitly permits both.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-banking-operations/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── auth-endpoints.md      # Phase 1 output
│   └── banking-endpoints.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
banking_app/                   # Django project configuration package
├── __init__.py
├── settings.py
├── urls.py
└── wsgi.py

accounts/                      # Authentication & user management app
├── __init__.py
├── admin.py
├── apps.py
├── forms.py                   # RegistrationForm, LoginForm
├── managers.py                # CustomUserManager
├── models.py                  # CustomUser
├── urls.py
├── views.py
├── templates/
│   └── accounts/
│       ├── signup.html
│       ├── login.html
│       ├── password_reset.html
│       ├── password_reset_done.html
│       ├── password_reset_confirm.html
│       └── password_reset_complete.html
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── test_models.py
    └── test_views.py

banking/                       # Banking operations app
├── __init__.py
├── admin.py
├── apps.py
├── forms.py                   # DepositForm, WithdrawForm, TransferForm
├── models.py                  # Account, Transaction
├── services.py                # Atomic money operations (deposit, withdraw, transfer)
├── urls.py
├── views.py
├── templates/
│   └── banking/
│       ├── dashboard.html
│       └── transactions.html
└── tests/
    ├── __init__.py
    ├── factories.py
    ├── test_models.py
    ├── test_services.py
    └── test_views.py

templates/                     # Shared base templates
└── base.html

static/                        # CSS / JS assets

manage.py
requirements.txt               # Production dependencies (pinned)
requirements-dev.txt           # Dev/test dependencies (pinned)
.env.example                   # Template for local .env file
.pre-commit-config.yaml        # flake8 + pylint + bandit hooks
```

**Structure Decision**: Two-app Django project — `accounts` for authentication
and user management; `banking` for money operations. A `services.py` module in
`banking` isolates all atomic transaction logic from views, keeping views thin
and service logic independently testable.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| SonarQube CI not configured (Principle III — Prototype tier) | Prototype scope; SonarQube infrastructure (server, CI token, project key) is disproportionate for a learning project | flake8 + pylint + bandit in pre-commit hooks provides adequate static analysis; SonarQube MUST be added before any production deployment |
| `select_for_update()` omitted; SQLite3 used instead of PostgreSQL (Principle V — Prototype tier) | User explicitly chose SQLite3; no external DB server dependency; constitution v1.1.0 Prototype tier permits this | `@transaction.atomic` wraps all balance mutations; SQLite3's exclusive write-lock prevents concurrent corruption at prototype scale; PostgreSQL migration requires only `DATABASES` config change + adding `select_for_update()` to service functions |

## Production Migration TODO

Before real users or real money are involved:

- [ ] Switch to PostgreSQL (`DATABASES` in `settings.py`)
- [ ] Add `select_for_update()` to all atomic balance operations in `banking/services.py`
- [ ] Set up SonarQube CI integration and enforce Quality Gate
- [ ] Enable `SECURE_SSL_REDIRECT = True`, HSTS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- [ ] Configure real SMTP email backend
- [ ] Run `python manage.py check --deploy`
- [ ] Promote to Production tier in this plan

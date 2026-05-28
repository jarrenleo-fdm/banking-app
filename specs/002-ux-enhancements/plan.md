# Implementation Plan: UX Enhancements

**Branch**: `007-mcp-api-key-auth` (feature pinned to `specs/002-ux-enhancements`) | **Date**: 2026-05-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/002-ux-enhancements/spec.md`

## Summary

Six user-facing improvements to the existing Django banking application: real-time password criteria guidance on registration, password reset, and signed-in password change; counterparty names and transaction IDs in transaction history; optional transfer descriptions; optional initial balance on registration; and a signed-in user details and credentials update flow for name, username, email address, phone number, and password. No model schema changes are required because the affected fields already exist.

## Technical Context

**Language/Version**: Python 3.11+ / Django 5.2
**Primary Dependencies**: Django 5.2, django-environ, Argon2 password hasher
**Storage**: SQLite3 prototype storage
**Testing**: pytest + pytest-django + factory-boy; coverage via pytest-cov
**Target Platform**: Local development server; Linux server before production hardening
**Project Type**: Django web application with server-rendered HTML templates
**Performance Goals**: Standard web application page loads under 2 seconds on the development server
**Constraints**: No JavaScript build pipeline; no new Python dependencies; preserve existing custom user model and phone-number normalization
**Scale/Scope**: Prototype / learning application; one personal account per user; business-account role flows remain out of scope for this feature

## Constitution Check

**Active Tier**: Prototype / Learning

*GATE: Pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Security & Confidentiality First | Pass | Password criteria are enforced server-side as well as shown in the UI. User details and credential updates require authentication, validate unique identifiers, and do not expose another user's private details in errors. Password changes require the current password. |
| II. Test-First Development | Pass | Implementation must add failing tests before each story change, including profile, username, and password-change validation tests. |
| III. Code Quality Gates | Prototype deviation | SonarQube CI is not required in this tier; local flake8, pylint, and bandit remain required compensating controls. |
| IV. Auditability & Observability | Pass | Transaction records remain immutable. User details and credential updates should emit a security-relevant audit/log event that identifies the acting user and changed field names without logging raw PII or passwords. |
| V. Data Integrity & Transactional Consistency | Pass | Money movement continues through existing atomic services using Decimal. The initial balance path delegates to deposit so account balances reconcile against transaction history. Profile and credential updates do not mutate balances. |

## Project Structure

### Documentation (this feature)

```text
specs/002-ux-enhancements/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── services.md
│   └── views.md
└── tasks.md
```

### Source Code (affected files)

```text
accounts/
├── forms.py                         # RegistrationForm, UserDetailsForm, PasswordChangeForm usage
├── validators.py                    # PasswordComplexityValidator
├── views.py                         # signup plus user details and credential update view
├── urls.py                          # user details route
├── tests/
│   ├── test_forms.py
│   ├── test_validators.py
│   └── test_views.py
└── templates/accounts/
    ├── signup.html
    ├── password_reset_confirm.html
    └── profile.html                 # user details and credential update page

banking/
├── forms.py                         # TransferForm description field
├── services.py                      # transfer(description=...)
├── tests/
│   ├── test_services.py
│   └── test_views.py
└── templates/banking/
    ├── dashboard.html
    └── transactions.html

banking_app/
└── settings.py                      # PasswordComplexityValidator registration

static/
└── js/
    └── password-criteria.js
```

**Structure Decision**: Use the existing `accounts` app for authentication, identity, and credential changes; the existing `banking` app for transaction and transfer UX changes; and a single static JavaScript file for password criteria behavior. User details, username, and password updates are account-management concerns and do not belong in `banking/services.py`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| SonarQube CI not required | Prototype / Learning tier keeps operational infrastructure minimal | Local flake8, pylint, bandit, and pytest are the existing compensating controls |
| SQLite3 without row-level locking | Prototype / Learning tier uses SQLite3 | Existing `@transaction.atomic` money services are sufficient for the single-user prototype tier |

## Phase 0: Research

Research outputs are captured in [research.md](research.md). Key decisions:

- Keep existing database schema; `CustomUser`, `Account`, and `Transaction` already contain the required fields.
- Add a backend password validator so visual password criteria match enforced rules.
- Pass transfer descriptions through the existing banking service layer.
- Use the existing deposit service for non-zero initial balance so balance history reconciles.
- Add a dedicated authenticated user details form and route; username is editable with format and uniqueness validation.
- Add a signed-in password change form that requires the current password and reuses the same password criteria.
- Log user details and credential updates as security-relevant events without raw PII or passwords.

## Phase 1: Design & Contracts

Design outputs:

- [data-model.md](data-model.md): existing entity fields, validation rules, and profile/credential update state behavior.
- [contracts/services.md](contracts/services.md): modified `transfer()` service contract, password validator contract, and account update form/view responsibilities.
- [contracts/views.md](contracts/views.md): account-facing view/form contracts for signup, password reset criteria, and user details and credential updates.
- [quickstart.md](quickstart.md): local verification steps for all six UX stories.

**Post-Design Constitution Check**: Pass. The design adds no new schema, keeps money mutations inside existing atomic services, requires tests first, requires current-password verification for password changes, and includes non-PII audit/log events for user details and credential updates.

## Implementation Order

Tasks should continue to follow Red-Green-Refactor:

1. Write failing tests for the story or validation branch.
2. Implement the smallest change that passes.
3. Run the focused pytest target.
4. Run pre-commit before handoff when practical.

Recommended story order:

1. Password criteria guidance and backend enforcement.
2. Transfer counterparty visibility and transaction IDs.
3. Transfer descriptions.
4. User details and credential update flow.
5. Optional initial balance on registration.
6. Full regression and manual quickstart verification.

## Production Migration TODO

Before real users or real money are involved, migrate to the Production tier:

- Switch from SQLite3 to PostgreSQL.
- Add row-level locking to balance-modifying service functions where appropriate.
- Integrate SonarQube into CI and enforce the Quality Gate.
- Review HTTPS, secure cookies, CSRF, HSTS, and deployment settings with `python manage.py check --deploy`.
- Replace development email/password-reset assumptions with production SMTP and operational monitoring.

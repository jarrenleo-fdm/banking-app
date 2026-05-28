<!-- SPECKIT START -->

For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan at
specs/002-ux-enhancements/plan.md

<!-- SPECKIT END -->

# AI Agent Working Guide

## First Reads

- [AGENTS.md](AGENTS.md) for workspace-wide instructions.
- [specs/002-ux-enhancements/plan.md](specs/002-ux-enhancements/plan.md), [specs/002-ux-enhancements/spec.md](specs/002-ux-enhancements/spec.md), and [specs/002-ux-enhancements/tasks.md](specs/002-ux-enhancements/tasks.md) for the current UX enhancements feature.
- [README.md](README.md) for baseline domain context, but verify business-account details against code and `specs/003-business-account/` because parts of the README still describe the older `BusinessProfile` model.
- [specs/001-core-banking-operations/quickstart.md](specs/001-core-banking-operations/quickstart.md) for local setup, data formats, and baseline validation.
- [specs/006-banking-mcp-server/quickstart.md](specs/006-banking-mcp-server/quickstart.md) when changing [mcp_server/](mcp_server/).
- For any feature work, read that feature's `spec.md`, `plan.md`, `tasks.md`, `quickstart.md`, and any files under `contracts/` before editing code.

## Project Snapshot

- Stack: Django 5.2, Python 3.11+, pytest/pytest-django, SQLite prototype storage, server-rendered HTML templates.
- Runtime dependencies live in [requirements.txt](requirements.txt); dev/test/lint dependencies live in [requirements-dev.txt](requirements-dev.txt).
- [accounts/](accounts/) owns authentication, the custom user model, signup/login/password-reset flows, forms, validators, and account-facing tests.
- [banking/](banking/) owns personal accounts, business accounts, billers, transaction models, money movement services, views, URLs, templates, context processors, migrations, and tests.
- [banking_app/](banking_app/) owns Django settings, ASGI/WSGI, and root URL routing.
- [mcp_server/](mcp_server/) exposes banking actions through a FastMCP JSON-RPC stdio server and has its own pytest suite.
- [templates/](templates/) contains shared base templates; [static/](static/) contains CSS and JavaScript such as theme and password-criteria behavior.
- Specs under [specs/](specs/) are feature artifacts. Treat the feature directory in [.specify/feature.json](.specify/feature.json) as active unless the user says otherwise.

## Spec Map

- [specs/001-core-banking-operations/](specs/001-core-banking-operations/) defines the baseline app: custom username login, email password reset, Singapore-style phone numbers, one personal `Account` per `CustomUser`, deposits, withdrawals, phone-number transfers, and immutable personal `Transaction` history.
- [specs/002-ux-enhancements/](specs/002-ux-enhancements/) adds password criteria guidance, backend password complexity enforcement, visible transaction IDs/counterparties, optional transfer descriptions, optional initial balance on personal signup, and authenticated user details plus credential updates.
- [specs/003-business-account/](specs/003-business-account/) is the active business-account source of truth. It defines standalone `BusinessAccount`, generated manager and authoriser users, the 7,000 minimum balance floor, manager pending submissions, authoriser direct execution, and manager read-only pending queue.
- [specs/004-billing-system/](specs/004-billing-system/) defines personal billers and bill payments: five fixed categories, mandatory `reference`, uniqueness on `(account, name, reference)`, and bill payments recorded as `Transaction.BILL_PAYMENT`.
- [specs/005-theme-toggle/](specs/005-theme-toggle/) defines the light/dark theme toggle: `data-theme` on `<html>`, `localStorage` key `theme`, OS preference fallback, no database changes, and edits limited to shared templates plus `static/css/styles.css` and `static/js/theme.js`.
- [specs/006-banking-mcp-server/](specs/006-banking-mcp-server/) defines the personal-only FastMCP stdio server. MCP login is API-key-only via `login_with_api_key`; existing-account reads and writes require an API-key-backed session token; open personal signup requires no token; all business-account MCP tools are out of scope.

## Setup, Run, and Verify

Use these commands for local setup and validation:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
pytest
```

Useful narrower checks:

```bash
pytest accounts/tests/ banking/tests/ -v
pytest banking/tests/test_services.py -v
pytest mcp_server/tests/ -v
pytest --cov=accounts --cov=banking --cov-report=term-missing
python manage.py check
python -m mcp_server
```

Prefer `pytest` over Django's test runner. `pytest.ini` sets `DJANGO_SETTINGS_MODULE = banking_app.settings`.

## Quality Gates

- Run [pre-commit](.pre-commit-config.yaml) before handoff when practical:

```bash
pre-commit run --all-files
```

- Hooks enforce flake8 (`--max-line-length=88`), bandit over `accounts`, `banking`, and `banking_app`, and pylint over those same Django packages.
- If a hook fails because of pre-existing or unrelated worktree changes, report that clearly instead of rewriting unrelated code.

## Conventions That Matter

- Custom user model is active: `AUTH_USER_MODEL = "accounts.CustomUser"` in [banking_app/settings.py](banking_app/settings.py). Do not import or assume Django's default `User` model; use `get_user_model()` where needed.
- Phone numbers are Singapore-style 8 digit strings beginning with `8` or `9`; user save logic normalizes spaces and hyphens.
- Each new `CustomUser` receives a personal [banking.models.Account](banking/models.py) through a post-save signal.
- Money movement business logic belongs in [banking/services.py](banking/services.py). Views should call services and translate domain errors into form errors/messages.
- Use `Decimal` for all money. Never introduce float arithmetic for balances or transaction amounts.
- Wrap balance mutations in transactions. Existing services use `@transaction.atomic`; business-account immediate execution paths use `select_for_update()`.
- Tests for banking services and views belong under [banking/tests/](banking/tests/); account/auth tests belong under [accounts/tests/](accounts/tests/).
- After model/schema edits, generate and commit migrations under [accounts/migrations/](accounts/migrations/) or [banking/migrations/](banking/migrations/).
- Keep transaction records immutable. Personal account history uses `Transaction`; business account history uses `BusinessTransaction`.
- Preserve the role branch order in dashboard and money-movement views: manager first, authoriser second, personal account fallback last.

## Business Account Notes

- Current business-account model is standalone [BusinessAccount](banking/models.py), not an `Account.account_type = BUSINESS` variant.
- `AccountManagerProfile` links one manager user to one `BusinessAccount`; `Authoriser` links one authoriser user to one `BusinessAccount`.
- Manager and authoriser users still get personal `Account` rows from the signal, but business-role screens must use `BusinessAccount` as the single source of truth.
- Public business signup is `/business/create/`; it calls `create_business_account_mock`, creates the business, manager user, and authoriser user, and displays generated credentials once.
- Business initial deposit must be at least `7000.00`. Outgoing business transactions must not reduce balance below `7000.00`.
- Manager deposits execute immediately. Manager withdrawals, transfers, and bill payments create `PendingTransaction` rows for authoriser approval.
- Authoriser deposits, withdrawals, transfers, and bill payments execute immediately and write `BusinessTransaction` audit records.
- Both manager and authoriser can view pending transactions; manager view is read-only at `/banking/pending/`, while authoriser approval/rejection is under `/banking/authorise/`.
- For business-account behavior, treat [specs/003-business-account/spec.md](specs/003-business-account/spec.md), [specs/003-business-account/plan.md](specs/003-business-account/plan.md), [specs/003-business-account/contracts/views.md](specs/003-business-account/contracts/views.md), and the current code as source of truth.

## Personal Banking Notes

- Personal dashboard routes live in [banking/urls.py](banking/urls.py) under paths such as `/dashboard/`, `/banking/deposit/`, `/banking/withdraw/`, `/banking/transfer/`, and `/banking/transactions/`.
- Personal biller and bill-payment flows use `Biller`, `BillerForm`, `BillPaymentForm`, and the billing templates under [banking/templates/banking/](banking/templates/banking/).
- Transfers identify recipients by phone number in both web services and the personal MCP server.
- Personal signup supports optional `initial_balance`; blank or explicit zero means `0.00`, while positive values update the auto-created account after user creation.
- Password requirements include minimum length plus uppercase, lowercase, digit, and special-character checks. Keep frontend criteria and `accounts.validators.PasswordComplexityValidator` aligned.
- Transfer descriptions are optional, max 200 characters, and must be stored on both outgoing and incoming `Transaction` records.

## Billing Notes

- `Biller.name` stores the fixed category value, not a free-text payee name. Valid values are `ELECTRICITY`, `WATER_UTILITIES`, `INTERNET_BROADBAND`, `TELECOMMUNICATIONS`, and `TOWN_COUNCIL`.
- `Biller.reference` is mandatory. The database and form validation enforce uniqueness per `(account, name, reference)`.
- Bill payment history is part of immutable personal `Transaction` history with `transaction_type = BILL_PAYMENT` and a description that includes category display plus reference.

## Theme Notes

- Theme preference is client-side only. Do not add models, migrations, views, or URLs for the theme toggle.
- `templates/base.html` and `templates/base_auth.html` are the shared integration points for the toggle and no-flash init script.
- `static/js/theme.js` owns toggle behavior; `static/css/styles.css` owns light/dark CSS custom property tokens.

## MCP Server Notes

- MCP server entry point: [mcp_server/__main__.py](mcp_server/__main__.py), which calls `main()` from [mcp_server/__init__.py](mcp_server/__init__.py).
- Tool implementations live in [mcp_server/server.py](mcp_server/server.py) and wrap Django service calls with FastMCP.
- Run with:

```bash
python -m mcp_server
```

- MCP uses API-key-backed token auth in [mcp_server/auth.py](mcp_server/auth.py). Existing-account read and write tools require a session token from `login_with_api_key`; open personal signup does not require a session token.
- Users can create MCP API keys at `/accounts/api-keys/`; keys belong to `accounts.CustomUser`, store only hashed secrets, and display the raw key once after creation.
- MCP clients can call `login_with_api_key` to receive a short-lived session token; username/password MCP login is not part of the personal MCP server.
- Revoking an API key must block future API-key login and protected actions from sessions that were created by that key.
- The token store is in-memory and expires tokens after `MCP_SESSION_TIMEOUT_MINUTES` of inactivity, defaulting to 15 minutes.
- MCP amount validation must reject non-decimal input, non-positive values for write amounts, and more than two decimal places before delegating to services.
- MCP tool responses should serialize `Decimal` values as strings and return structured `{"error": "..."}` dictionaries for failures.
- Business account lookup, business transaction history, pending approvals, approval/rejection, and business signup must not be exposed by the personal MCP server.
- `mcp_server/tests/` is the authority for MCP behavior. Add or update tests there before changing tools.
- MCP tests are scoped under [mcp_server/tests/](mcp_server/tests/):

```bash
pytest mcp_server/tests/ -v
```

## Environment And Safety

- `.env.example` documents local environment variables. Defaults are development-oriented; do not treat this prototype as production-safe.
- Local database is [db.sqlite3](db.sqlite3). Do not delete or reset it unless the user explicitly asks.
- Before real users or real money, the project plans call for PostgreSQL, stronger locking, HTTPS/secure cookie review, real SMTP, SonarQube CI, and `python manage.py check --deploy`.
- The worktree may contain user changes. Never revert unrelated changes; inspect and work with files you need to touch.

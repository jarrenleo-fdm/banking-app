# Quickstart: Core Banking Operations

Branch: `001-core-banking-operations`

---

## Prerequisites

- Python 3.11 or higher
- Git
- A terminal (macOS/Linux) or PowerShell (Windows)

---

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd banking-app

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install production dependencies
pip install -r requirements.txt

# 4. Create your local environment file
cp .env.example .env
```

Open `.env` and set at minimum:

```dotenv
SECRET_KEY=<generate below>
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

Generate a `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

```bash
# 5. Apply database migrations (creates db.sqlite3)
python manage.py migrate

# 6. (Optional) Create an admin superuser
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

Open **http://127.0.0.1:8000/** in your browser.

---

## Key Formats

### Phone Number

Phone numbers must be exactly **8 digits** with the first digit **8 or 9**.

| Valid | Invalid |
|-------|---------|
| `81234567` | `12345678` (starts with 1) |
| `91234567` | `8123456` (only 7 digits) |
| `8123 4567` *(normalized automatically)* | `+6581234567` (country code not accepted) |

Phone numbers are used at registration and as the recipient identifier when
sending money.

### Password Rules

Passwords must:
- Be at least 8 characters long
- Not be entirely numeric
- Not be a commonly used password (e.g., "password123")

---

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=accounts --cov=banking --cov-report=term-missing

# Run a specific test file
pytest banking/tests/test_services.py -v
```

Tests follow Red-Green-Refactor. All money-handling paths have both unit and
integration test coverage.

---

## Password Reset (Development)

Password reset emails are printed to the terminal (console email backend).
After submitting a reset request at `/accounts/password-reset/`, look in the
terminal for the reset link.

---

## Admin Panel

Visit **http://127.0.0.1:8000/admin/** and log in with the superuser credentials
created in step 6. From there you can inspect users, accounts, and transactions.

---

## Project Layout

```
banking_app/    Django project configuration (settings, root URLs)
accounts/       Authentication: sign up, log in, password reset
banking/        Banking: dashboard, deposit, withdraw, transfer, history
templates/      Shared HTML base template
static/         CSS / JS assets
manage.py       Django management entry point
```

---

## Production Checklist

**Before real users or real money** — see Production Migration TODO in
`specs/001-core-banking-operations/plan.md`.

Key items:
- Switch database to PostgreSQL
- Enable HTTPS and secure cookie flags
- Configure SonarQube CI
- Set up real SMTP email
- Run `python manage.py check --deploy`

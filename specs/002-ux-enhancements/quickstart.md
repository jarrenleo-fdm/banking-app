# Quickstart: Verifying UX Enhancements Locally

## Prerequisites

- Python virtual environment activated with `requirements-dev.txt` installed
- `.env` file present (copy from `.env.example`)
- Database migrated: `python manage.py migrate`

## 1. Run the test suite

```bash
pytest --cov=accounts --cov=banking --cov-report=term-missing
```

All tests must pass and coverage must not drop below 80% on new code.

## 2. Start the development server

```bash
python manage.py runserver
```

## 3. Verify: Password criteria checklist

1. Navigate to `http://127.0.0.1:8000/accounts/signup/`
2. Click into the Password field — the criteria checklist should appear
3. Type a password character by character — each criterion checks off in real time:
   - ✓ At least 8 characters
   - ✓ One uppercase letter (A–Z)
   - ✓ One lowercase letter (a–z)
   - ✓ One digit (0–9)
   - ✓ One special character
4. Submit a password that fails one criterion — the form must reject it and highlight the unmet rule
5. Repeat at `http://127.0.0.1:8000/accounts/password-reset/` → follow reset flow to the confirm page

## 4. Verify: Transfer description

1. Register two accounts (open a second browser or incognito window)
2. On account A's dashboard, fill in the Transfer card with account B's phone number, an amount, and a description (e.g., "Rent May")
3. Submit — success message should appear
4. On account A: navigate to Transaction History — the TRANSFER_OUT entry should show the description "Rent May"
5. Log in as account B: navigate to Transaction History — the TRANSFER_IN entry should also show "Rent May"
6. Send another transfer with no description — the history entry must not show a description label

## 5. Verify: Transaction ID and counterparty in history

1. In Transaction History (either account), verify each row shows a Transaction ID (numeric)
2. Verify TRANSFER_OUT rows show the recipient's name; TRANSFER_IN rows show the sender's name
3. DEPOSIT and WITHDRAWAL rows must have no counterparty shown

## 6. Verify: Initial balance on registration

1. Navigate to `http://127.0.0.1:8000/accounts/signup/`
2. Fill out the form including an Initial Balance of `500.00`
3. Log in and check the dashboard — balance should read $500.00
4. Register again with the Initial Balance field left blank — balance should read $0.00
5. Attempt to register with Initial Balance `-100` — form must reject with a validation error

## 7. Static analysis

```bash
pre-commit run --all-files
```

All hooks (flake8, pylint, bandit) must pass with no errors.

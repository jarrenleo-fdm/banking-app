# Quickstart: Billing System

## Prerequisites

- Python 3.11+, Django project running (existing setup)
- `python manage.py migrate` applied after adding new migration

## Running Locally

```bash
python manage.py migrate
python manage.py runserver
```

Navigate to `/banking/billing/` while logged in.

## Manual Smoke Test

1. Log in to any user account.
2. Go to `/banking/billing/` — should see an empty billers list and the "Add biller" form.
3. Add a biller (select category e.g. Electricity, reference: "ACC-12345" — **reference is required**) → biller appears in the list.
   - Try submitting without a reference → form error shown, no biller created.
   - Add a second Electricity biller with the same reference → duplicate error shown.
   - Add a second Electricity biller with a different reference (e.g., "ACC-67890") → succeeds; both appear in the list with distinct labels.
4. Select the biller, enter an amount ≤ your balance, submit → success message, balance decreases.
5. Go to `/banking/billing/history/` → the payment appears with biller name, amount, and date.
6. Go to `/banking/banking/transactions/` → the same payment appears as a "Bill Payment" entry.
7. Remove the biller → it disappears from the list; history entry is unchanged.

## Running Tests

```bash
python -m pytest banking/tests/
```

All tests for the billing feature live in the existing test files following the project convention.

## Linting (Prototype tier — local gates)

```bash
flake8 banking/
pylint banking/
bandit -r banking/
```

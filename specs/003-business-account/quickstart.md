# Quickstart: Verify Business Account Registration

## Prerequisites

```bash
cd /path/to/banking-app
python manage.py migrate
python manage.py runserver
```

## Verify: Business Account Registration

1. Open `http://127.0.0.1:8000/accounts/signup/` in a browser.
2. Confirm "Personal" is selected by default and business fields are hidden.
3. Select "Business" — confirm company name and registration number fields appear.
4. Fill in all fields:
   - Name: Test Corp
   - Username: testcorp
   - Email: testcorp@example.com
   - Phone: 81234567
   - Password: Abc@12345
   - Company Name: Test Corp Pte Ltd
   - Business Registration Number: ABC12345
5. Submit. Confirm redirect to dashboard.
6. On dashboard, confirm account type label shows "Business".

## Verify: Validation Errors

1. Select "Business", leave company name blank, submit → expect field error on company name.
2. Select "Business", enter a registration number already used → expect "This registration number is already in use."
3. Select "Business", enter a registration number shorter than 6 chars (e.g. `AB1`) → expect format error.
4. Select "Personal", submit without business fields → expect successful personal account creation.

## Verify: Personal Account Unchanged

1. Register a new personal account (no business fields).
2. Confirm dashboard shows "Personal" label.
3. Confirm all banking operations (deposit, withdrawal, transfer) work normally.

## Run Tests

```bash
pytest accounts/tests/test_views.py banking/tests/test_models.py -v
```

All tests must pass with no failures.

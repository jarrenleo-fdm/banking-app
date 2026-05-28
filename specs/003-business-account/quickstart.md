# Quickstart: Business Account (Revised Model)

## Prerequisites

```bash
cd /path/to/banking-app
python manage.py migrate
python manage.py runserver
```

No superuser required. All accounts are created via the public form.

---

## Flow 1 — Create a Business Account

1. Open `http://127.0.0.1:8000/business/create/`
2. Fill in the form:
   - **Company Name**: Acme Corp
   - **UEN**: 202512345A
   - **Street**: 1 Marina Boulevard
   - **City**: Singapore
   - **Postal Code**: 018989
   - **Initial Deposit**: 10000
3. Click **Create Business Account**
4. The confirmation screen shows — **save these credentials**:

   | Role | Username | Password | Phone |
   |------|----------|----------|-------|
   | Account Manager | `manager.acmecorp` | `Demo@xxxxxx` | `80000001` |
   | Authoriser | `authoriser.acmecorp` | `Demo@yyyyyy` | `80000002` |

   Business account balance is **$10,000.00** and the initial deposit appears in the transaction history.

   Credentials are shown **once only**. Refreshing this page redirects back to the form.

---

## Flow 2 — Account Manager Submits a Deposit

1. Open `http://127.0.0.1:8000/accounts/login/`
2. Log in as the **account manager** (`manager.acmecorp`)
3. Dashboard shows the business account: **Acme Corp**, balance **$10,000.00**
4. Under **Deposit**, enter `5000.00` and click **Deposit**
5. Confirm: balance is now **$15,000.00** and a deposit appears in transaction history

---

## Flow 3 — Account Manager Submits an Outgoing Transaction

1. Still logged in as the account manager
2. Under **Withdraw**, enter `1000.00` and click **Withdraw**
3. Confirm: balance is still **$15,000.00** (not deducted yet)
4. A success banner reads: "Withdrawal submitted and awaiting authoriser approval."
5. Log out

---

## Flow 4 — Authoriser Approves the Pending Transaction

1. Log in as the **authoriser** (`authoriser.acmecorp`)
2. Dashboard shows a **"Pending Approvals (1)"** button in the navigation
3. Click it → pending transactions queue lists the **$1,000.00 withdrawal**
4. Click **Approve**
5. Confirm: flash message "Transaction approved and executed."
6. Log back in as the account manager → balance is now **$14,000.00**; withdrawal appears in history

---

## Flow 5 — Authoriser Rejects a Pending Transaction

1. As account manager, submit a new **Transfer** of `500.00` to another registered user
2. Log in as the authoriser → pending queue shows the transfer
3. Click **Reject**
4. Confirm: flash message "Transaction rejected."
5. Log in as account manager → balance unchanged; transaction history shows "Rejected: Transfer Out"

---

## Flow 6 — Authoriser Submits a Transaction Directly (FR-008a)

1. Log in as the **authoriser** (`authoriser.acmecorp`)
2. Dashboard shows the business account: **Acme Corp**, balance (current amount)
3. Under **Withdraw**, enter `2000.00` and click **Withdraw**
4. Confirm: balance **immediately decreases** by 2,000 — no pending queue entry created
5. Transaction history shows a new **Withdrawal** record for $2,000.00

No authoriser approval required — the authoriser's own transactions execute immediately.

---

## Flow 7 — Account Manager Views Read-Only Pending Queue (FR-009)

1. As account manager (`manager.acmecorp`), submit a withdrawal (see Flow 3)
2. Open `http://127.0.0.1:8000/banking/pending/`
3. Confirm: the pending transaction is listed (amount, type, timestamp)
4. Confirm: **no Approve or Reject buttons** are present — view is read-only
5. Attempt to POST to `/banking/authorise/<id>/approve/` as the manager → **403 Forbidden**

---

## Validation Checks

| Scenario | Expected behaviour |
|----------|--------------------|
| Blank company name on creation form | Field error: "This field is required." |
| Duplicate UEN | Field error: "A business account with this UEN already exists." |
| Initial deposit below 7,000 on creation form | Field error on initial deposit field; account not created |
| Account manager deposits negative amount | Field error: "Amount must be greater than zero." |
| Account manager withdrawal that would bring balance below 7,000 | Error: "Transaction would bring balance below minimum (7,000)."; no pending transaction created |
| Authoriser approves pending tx that would breach 7,000 floor | Auto-rejected; flash message "Transaction automatically rejected: minimum balance would be breached."; balance unchanged |
| Transfer to non-existent phone number | Error: "No account found with that phone number." |
| Visit `/business/created/` after credentials consumed | Redirect to `/business/create/` |
| Non-authoriser visits authoriser queue | 403 Forbidden |
| Authoriser submits withdrawal that would breach 7,000 floor | Error: "Transaction would bring balance below minimum (7,000)."; no BusinessTransaction created |
| Non-manager visits `/banking/pending/` | 403 Forbidden |
| Account manager attempts POST to approve/reject endpoint | 403 Forbidden |

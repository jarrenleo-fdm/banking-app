# Tasks: Business Account Registration

**Input**: Design documents from `/specs/003-business-account/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/views.md ✓, quickstart.md ✓

**Tests**: Included — Constitution §II (NON-NEGOTIABLE) requires Red-Green-Refactor for all service functions and views. Write tests first; verify they FAIL before implementing.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on other incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Paths are project-relative

---

## Phase 1: Setup — Remove Wrong Model Code

**Purpose**: Delete all wrong-model code (BusinessProfile, manage_authorisers flow, old business-branch logic) before introducing the new model. Prevents migration conflicts.

**⚠️ CRITICAL**: Must complete before Phase 2. Wrong-model migrations (0006/0007/0008) must be discarded.

- [X] T001 Assess migration state: run `python manage.py showmigrations banking` — if 0006/0007/0008 are unapplied, delete banking/migrations/0006_*.py, banking/migrations/0007_*.py, banking/migrations/0008_*.py to restore baseline at 0005; if applied, note this and squash in Phase 2's migration task
- [X] T002 [P] Delete `manage_authorisers.html` template at banking/templates/banking/manage_authorisers.html
- [X] T003 [P] Remove URL patterns for `manage_authorisers/`, `add/`, `<int:pk>/remove/`, `pending/`, `dashboard/dismiss-no-authoriser-warning/` from banking/urls.py
- [X] T004 [P] Delete `AddAuthoriserForm` from banking/forms.py
- [X] T005 Delete `manage_authorisers_view`, `add_authoriser_view`, `remove_authoriser_view`, `dismiss_no_authoriser_warning_view`, `pending_transactions_view` from banking/views.py; remove old business-branch logic in `withdraw_view`, `transfer_view`, `pay_bill_view`; remove no-authoriser banner logic in `dashboard_view` (new branches are added in Phase 4)
- [X] T006 Delete `BusinessProfile` model from banking/models.py; remove `account_type` CharField and its `PERSONAL`/`BUSINESS` choices from `Account` model in banking/models.py

**Checkpoint**: `python manage.py check` passes with no errors; no import references to BusinessProfile, AddAuthoriserForm, or removed views remain

---

## Phase 2: Foundational — Data Model & Migration

**Purpose**: Introduce the correct data model. All three user stories depend on these entities and the applied migration.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete and migration is applied.

- [X] T007 Add `BusinessAccount` model to banking/models.py with fields: `company_name` CharField(200), `uen` CharField(50) unique=True, `street` CharField(200), `city` CharField(100), `postal_code` CharField(20), `balance` DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00')), `created_at` DateTimeField(auto_now_add=True)
- [X] T008 [P] Add `AccountManagerProfile` model to banking/models.py with fields: `user` OneToOneField(CustomUser, CASCADE, related_name='manager_profile'), `business_account` OneToOneField(BusinessAccount, CASCADE, related_name='manager')
- [X] T009 [P] Add `BusinessTransaction` model to banking/models.py with fields: `business_account` ForeignKey(BusinessAccount, PROTECT, related_name='transactions'), `transaction_type` CharField(20, choices: DEPOSIT/WITHDRAWAL/TRANSFER_OUT/BILL_PAYMENT/REJECTED), `amount` DecimalField(12,2), `balance_after` DecimalField(12,2), `counterparty` ForeignKey(Account, SET_NULL, null=True, blank=True), `description` CharField(200, blank=True), `timestamp` DateTimeField(auto_now_add=True); Meta ordering=['-timestamp']
- [X] T010 Modify `Authoriser` model in banking/models.py: change `business_account` from ForeignKey→Account to OneToOneField(BusinessAccount, CASCADE, related_name='authoriser'); change `user` from ForeignKey to OneToOneField(CustomUser, PROTECT, related_name='authoriser_profile'); remove `assigned_by` ForeignKey field; remove `unique_together` constraint
- [X] T011 Modify `PendingTransaction` model in banking/models.py: rename field `account` → `business_account` as ForeignKey(BusinessAccount, PROTECT, related_name='pending_transactions'); remove `biller` ForeignKey; retain `counterparty` FK→Account SET_NULL null/blank; retain `description`, `status` (PENDING/APPROVED/REJECTED/CANCELLED), `decided_at`, `decided_by` fields
- [X] T012 Generate migration: run `python manage.py makemigrations banking --name business_account_revised_model`; review the generated migration file to confirm it covers BusinessAccount/AccountManagerProfile/BusinessTransaction creation, Authoriser and PendingTransaction alterations, account_type removal, BusinessProfile drop
- [X] T013 Apply migration: run `python manage.py migrate banking`; verify with `python manage.py showmigrations banking`
- [X] T014 [P] Register BusinessAccount, AccountManagerProfile, BusinessTransaction, Authoriser, PendingTransaction in banking/admin.py; remove BusinessProfile registration if present

**Checkpoint**: `python manage.py migrate` succeeds; `python manage.py shell -c "from banking.models import BusinessAccount, AccountManagerProfile, BusinessTransaction; print('OK')"` exits cleanly

---

## Phase 3: User Story 1 — Create Business Account (Priority: P1) 🎯 MVP

**Goal**: A public form at `/business/create/` runs mock SQL creating a BusinessAccount + AccountManagerProfile user + Authoriser user, then displays generated credentials once on `/business/created/`.

**Independent Test**: Visit `/business/create/`, fill in valid business name, UEN, and address; submit; confirm credentials for both manager and authoriser appear on screen; log in as each user.

### Tests for User Story 1 — Write FIRST, verify FAIL before implementing (Constitution §II)

- [X] T015 [P] [US1] Write service tests in banking/tests/test_services.py: `test_create_business_account_mock_creates_business_account`, `test_create_business_account_mock_creates_manager_and_authoriser_users`, `test_create_business_account_mock_generates_sequential_phone_numbers` (manager=odd 80000001+, authoriser=even 80000002+), `test_create_business_account_mock_returns_credentials_dict`, `test_create_business_account_mock_duplicate_uen_raises`, `test_create_business_account_mock_collision_increments_username_suffix`
- [X] T016 [P] [US1] Write view tests in banking/tests/test_views.py: `test_create_business_account_view_get_renders_form`, `test_create_business_account_view_post_valid_redirects_to_created`, `test_create_business_account_view_post_blank_field_returns_error`, `test_create_business_account_view_post_duplicate_uen_returns_error`, `test_business_account_created_view_with_credentials_in_session`, `test_business_account_created_view_no_session_redirects_to_create`, `test_business_account_created_view_clears_session_after_display`

### Implementation for User Story 1

- [X] T017 [US1] Implement `create_business_account_mock(company_name, uen, street, city, postal_code)` in banking/services.py wrapped in `@transaction.atomic`: create BusinessAccount; derive slug from company_name (lowercase, strip non-alphanumeric, truncate to 20 chars); generate usernames `manager.<slug>` / `authoriser.<slug>` with numeric suffix on collision; query existing phone numbers and assign next odd slot ≥ 80000001 to manager and next even slot ≥ 80000002 to authoriser; generate passwords as `"Demo@" + 6 random chars from letters+digits`; create CustomUser + Account (personal, zero balance) for each; create AccountManagerProfile and Authoriser linked to BusinessAccount; return dict with manager_username, manager_password, manager_phone, authoriser_username, authoriser_password, authoriser_phone
- [X] T018 [US1] Add `BusinessAccountCreationForm` to banking/forms.py: fields `company_name`, `uen`, `street`, `city`, `postal_code`; `clean()` validates all fields non-blank/non-whitespace; `clean_uen()` checks BusinessAccount uniqueness and raises ValidationError("A business account with this UEN already exists.") on duplicate
- [X] T019 [US1] Implement `create_business_account_view` (GET+POST, no `@login_required`) in banking/views.py: GET renders empty BusinessAccountCreationForm; POST validates form, calls `create_business_account_mock`, stores credentials in `request.session['business_created_credentials']`, redirects to `/business/created/?id=<biz_id>`; on invalid form re-renders with errors
- [X] T020 [US1] Implement `business_account_created_view` in banking/views.py: pops `request.session.pop('business_created_credentials', None)`; if None redirects to `/business/create/`; else renders template with credentials
- [X] T021 [P] [US1] Create banking/templates/banking/create_business_account.html: form with company_name, uen, street, city, postal_code fields; CSRF token; field-level error display; submit button labelled "Create Business Account"
- [X] T022 [P] [US1] Create banking/templates/banking/business_account_created.html: table with columns Role/Username/Password/Phone for manager and authoriser rows; prominent "one-time display" warning; link to log in or return to `/business/create/`
- [X] T023 [US1] Add URL patterns to banking/urls.py: `path('business/create/', create_business_account_view, name='create_business_account')` and `path('business/created/', business_account_created_view, name='business_account_created')` (no login_required wrapper)

**Checkpoint**: All T015/T016 tests pass; manually follow quickstart Flow 1 — credentials shown once, both users can log in

---

## Phase 4: User Story 2 — Account Manager Submits a Transaction (Priority: P1)

**Goal**: Account manager logs in and sees a business account dashboard. Deposits execute immediately; outgoing transactions (withdrawal, transfer, bill payment) enter pending state with balance unchanged.

**Independent Test**: Log in as manager.acmecorp, submit a deposit of $5,000 (balance updates to $5,000), then submit a withdrawal of $1,000 (balance stays at $5,000, PendingTransaction record created with status PENDING).

### Tests for User Story 2 — Write FIRST, verify FAIL before implementing (Constitution §II)

- [X] T024 [P] [US2] Write service tests in banking/tests/test_services.py: `test_deposit_to_business_increases_balance_and_creates_transaction`, `test_deposit_to_business_zero_amount_raises`, `test_deposit_to_business_negative_amount_raises`, `test_create_pending_withdrawal_creates_pending_tx_status_pending`, `test_create_pending_withdrawal_insufficient_funds_raises`, `test_create_pending_transfer_valid_creates_pending_tx`, `test_create_pending_transfer_recipient_not_found_raises`, `test_create_pending_transfer_insufficient_funds_raises`, `test_create_pending_bill_payment_creates_pending_tx_with_description`
- [X] T025 [P] [US2] Write view tests in banking/tests/test_views.py: `test_dashboard_view_as_account_manager_shows_business_account`, `test_dashboard_view_as_personal_user_unchanged`, `test_deposit_view_as_account_manager_updates_balance`, `test_withdraw_view_as_account_manager_creates_pending_balance_unchanged`, `test_withdraw_view_as_account_manager_insufficient_funds`, `test_transfer_view_as_account_manager_creates_pending`, `test_transfer_view_as_account_manager_recipient_not_found`, `test_pay_bill_view_as_account_manager_creates_pending`

### Implementation for User Story 2

- [X] T026 [US2] Add `deposit_to_business(business_account, amount)` to banking/services.py wrapped in `@transaction.atomic`: validate amount > 0 (raise ValidationError("Amount must be greater than zero.")); update BusinessAccount.balance; create BusinessTransaction(type='DEPOSIT', amount=amount, balance_after=new_balance)
- [X] T027 [US2] Add `create_pending_withdrawal(business_account, amount)`, `create_pending_transfer(business_account, amount, recipient_phone)`, `create_pending_bill_payment(business_account, amount, category, reference)` to banking/services.py, each `@transaction.atomic`: validate amount > 0; validate business_account.balance >= amount (raise ValidationError("Insufficient funds.")); for transfer look up Account by phone (raise ValidationError("No account found with that phone number.") if not found); create PendingTransaction with status='PENDING'; bill payment sets description="Category (reference)"
- [X] T028 [US2] Add `BusinessBillPaymentForm` to banking/forms.py: fields `category` CharField, `reference` CharField, `amount` DecimalField; no saved-biller lookup
- [X] T029 [US2] Modify `dashboard_view` in banking/views.py: if `hasattr(request.user, 'manager_profile')` — fetch BusinessAccount via manager_profile, fetch last 5 BusinessTransaction records, pass is_manager=True + business_account + balance + recent_transactions + deposit_form + withdraw_form + transfer_form + bill_pay_form(BusinessBillPaymentForm) to template; personal path unchanged
- [X] T030 [US2] Modify `deposit_view` in banking/views.py: if manager_profile exists, validate DepositForm, call deposit_to_business, redirect to dashboard; personal path unchanged
- [X] T031 [US2] Modify `withdraw_view` in banking/views.py: if manager_profile exists, validate WithdrawForm, call create_pending_withdrawal (no authoriser-existence check — authoriser always exists in new model), flash "Withdrawal submitted and awaiting authoriser approval.", redirect to dashboard; personal path unchanged
- [X] T032 [US2] Modify `transfer_view` in banking/views.py: if manager_profile exists, validate TransferForm, call create_pending_transfer, handle ValidationError for recipient-not-found and insufficient-funds, flash success and redirect; personal path unchanged
- [X] T033 [US2] Modify `pay_bill_view` in banking/views.py: if manager_profile exists, use BusinessBillPaymentForm, call create_pending_bill_payment, redirect to dashboard; personal saved-biller path unchanged
- [X] T034 [US2] Update banking/templates/banking/dashboard.html: add `{% if is_manager %}` block showing BusinessAccount company name, balance, recent BusinessTransaction history, and inline forms for deposit/withdraw/transfer/bill-pay; `{% else %}` block renders unchanged personal dashboard

**Checkpoint**: All T024/T025 tests pass; manually follow quickstart Flows 2 and 3 — deposit reflects immediately, withdrawal enters pending state with balance unchanged

---

## Phase 5: User Story 3 — Authoriser Approves or Rejects (Priority: P1)

**Goal**: Authoriser logs in and sees a pending queue link when transactions await action. Approve executes immediately and updates the balance; reject cancels and records as Rejected.

**Independent Test**: After manager submits a withdrawal, log in as authoriser.acmecorp, confirm pending queue link is visible, approve the transaction, verify balance decreases and transaction leaves the queue.

### Tests for User Story 3 — Write FIRST, verify FAIL before implementing (Constitution §II)

- [X] T035 [P] [US3] Write service tests in banking/tests/test_services.py: `test_approve_business_pending_sets_status_approved`, `test_approve_business_pending_updates_business_account_balance`, `test_approve_business_pending_creates_business_transaction`, `test_approve_business_pending_insufficient_funds_leaves_status_pending`, `test_reject_business_pending_sets_status_rejected`, `test_reject_business_pending_creates_rejected_business_transaction`, `test_reject_business_pending_balance_unchanged`
- [X] T036 [P] [US3] Write view tests in banking/tests/test_views.py: `test_authoriser_queue_view_lists_pending_transactions`, `test_authoriser_queue_view_empty_queue_shows_message`, `test_authoriser_queue_view_non_authoriser_returns_403`, `test_approve_transaction_view_valid_authoriser_redirects`, `test_approve_transaction_view_insufficient_funds_flashes_error`, `test_approve_transaction_view_wrong_authoriser_returns_403`, `test_reject_transaction_view_valid_authoriser_redirects`, `test_reject_transaction_view_wrong_authoriser_returns_403`
- [X] T037 [P] [US3] Write context processor tests in banking/tests/test_context_processors.py (create file if absent): `test_pending_count_for_authoriser_with_pending_transactions`, `test_pending_count_for_authoriser_with_no_pending_returns_zero`, `test_pending_count_for_non_authoriser_returns_zero`, `test_pending_count_for_anonymous_user_returns_zero`

### Implementation for User Story 3

- [X] T038 [US3] Add `approve_business_pending(pending_tx, decided_by)` to banking/services.py wrapped in `@transaction.atomic`: verify pending_tx.status == 'PENDING'; check BusinessAccount.balance >= pending_tx.amount (if not, leave status PENDING and raise ValidationError("Insufficient funds.")); update balance; set pending_tx.status='APPROVED', decided_by, decided_at=now(); create BusinessTransaction with correct type and balance_after
- [X] T039 [US3] Add `reject_business_pending(pending_tx, decided_by)` to banking/services.py wrapped in `@transaction.atomic`: verify pending_tx.status == 'PENDING'; set pending_tx.status='REJECTED', decided_by, decided_at=now(); create BusinessTransaction(type='REJECTED', amount=pending_tx.amount, balance_after=current_balance — balance unchanged on reject)
- [X] T040 [US3] Modify `authoriser_queue_view` in banking/views.py: if user lacks `authoriser_profile` return HttpResponseForbidden("You are not assigned as an authoriser."); else fetch pending_txns = PendingTransaction.objects.filter(business_account=request.user.authoriser_profile.business_account, status='PENDING'); render authoriser_queue.html with pending_txns
- [X] T041 [US3] Modify `approve_transaction_view` in banking/views.py: fetch PendingTransaction by id; if pending_tx.business_account.authoriser.user != request.user return 403; call approve_business_pending; on success flash "Transaction approved and executed."; on ValidationError flash error message; redirect to authoriser queue
- [X] T042 [US3] Modify `reject_transaction_view` in banking/views.py: same authorization check as T041; call reject_business_pending; flash "Transaction rejected."; redirect to authoriser queue
- [X] T043 [US3] Rewrite `authoriser_pending_count` in banking/context_processors.py: if request.user is authenticated and has `authoriser_profile`, return `{'authoriser_pending_count': PendingTransaction.objects.filter(business_account=request.user.authoriser_profile.business_account, status='PENDING').count()}`; else return `{'authoriser_pending_count': 0}`
- [X] T044 [US3] Update banking/templates/banking/authoriser_queue.html: list each pending transaction with amount, type, description, submitted time; per-row POST forms for approve and reject with CSRF tokens; empty-queue message when no pending transactions exist
- [X] T045 [P] [US3] Update navigation in templates/base.html (or equivalent): render "Pending Approvals ({{ authoriser_pending_count }})" link to `/banking/authorise/` when `authoriser_pending_count > 0`; hide entirely when 0

**Checkpoint**: All T035/T036/T037 tests pass; manually follow quickstart Flows 4 and 5 and all Validation Checks

---

## Phase N: Polish & Cross-Cutting Concerns

**Purpose**: End-to-end validation and verification of all quickstart flows against the full test suite.

- [X] T046 [P] Verify banking/templates/banking/transactions.html and banking/templates/banking/billing_history.html are not served to manager users (or show appropriate empty state); update views/templates if they error for manager accounts
- [X] T047 Run full test suite: `pytest` — all tests pass; no regressions in personal account flows (accounts/tests/, banking/tests/)
- [X] T048 Manually run all quickstart.md Validation Checks: duplicate UEN, blank required field, negative deposit amount, withdrawal exceeding balance, transfer to non-existent phone, direct visit to `/business/created/` after credentials consumed, non-authoriser visiting `/banking/authorise/`
- [X] T049 [P] Confirm banking/admin.py exposes BusinessAccount, AccountManagerProfile, BusinessTransaction, Authoriser, PendingTransaction with no import errors at `/admin/`

**Checkpoint**: `pytest` green; all 7 validation checks from quickstart.md behave as documented; no 500 errors on any path in contracts/views.md

---

## Phase 6: Minimum Balance Floor (Post-Clarification 2026-05-26)

**Goal**: Implement the 7,000 minimum balance requirement across creation, outgoing-transaction submission, and authoriser approval. Supersedes the earlier insufficient-funds handling in `create_pending_*` and `approve_business_pending`.

**Affected files**: `banking/tests/test_services.py`, `banking/services.py`, `banking/forms.py`, `banking/views.py`, `banking/templates/banking/create_business_account.html`, `mcp_server/server.py`

**Independent Test**: (a) Visit `/business/create/`, enter initial deposit of 6,999 — form error shown; (b) log in as manager with balance $8,000, submit withdrawal of $1,500 — error shown, no pending tx created; (c) log in as authoriser, approve a pending tx that would bring balance to $6,500 — auto-rejected, flash error, balance unchanged.

### Tests for Phase 6 — Write FIRST, verify FAIL before implementing T055–T062 (Constitution §II)

> **NOTE: Write these tests FIRST. Run `python manage.py test banking` to confirm RED before T055.**

- [X] T050 [US1] Update all 6 existing `test_create_business_account_mock_*` call sites in `banking/tests/test_services.py` to pass `initial_deposit=Decimal("10000.00")` as a keyword argument — these calls currently omit `initial_deposit` and will raise `TypeError` once T055 adds the required parameter
- [X] T051 [P] [US1] Add 3 new failing tests to `banking/tests/test_services.py`:
  - `test_create_business_account_mock_sets_balance_to_initial_deposit`: call with `initial_deposit=Decimal("10000.00")`, assert `BusinessAccount.objects.get(uen=...).balance == Decimal("10000.00")`
  - `test_create_business_account_mock_records_initial_deposit_as_business_transaction`: same call, assert `BusinessTransaction.objects.filter(business_account=..., transaction_type=BusinessTransaction.DEPOSIT, amount=Decimal("10000.00")).exists()`
  - `test_create_business_account_mock_initial_deposit_below_7000_raises`: call with `initial_deposit=Decimal("6999.99")`, assert `pytest.raises(BankingError)`
- [X] T052 [US2] Update 4 existing `create_pending_*` tests in `banking/tests/test_services.py` that deposit `Decimal("500.00")` — change to `Decimal("8000.00")` so they remain GREEN after T059 tightens the guard (balance of 500 minus any amount is always < 7,000):
  - `test_create_pending_withdrawal_creates_pending_tx_status_pending`
  - `test_create_pending_transfer_valid_creates_pending_tx`
  - `test_create_pending_transfer_recipient_not_found_raises`
  - `test_create_pending_bill_payment_creates_pending_tx_with_description`
- [X] T053 [P] [US2] Add 3 new failing tests to `banking/tests/test_services.py` (each deposits `Decimal("8000.00")`, then submits `Decimal("1500.00")` — leaving $6,500 < $7,000, expects `InsufficientFundsError`):
  - `test_create_pending_withdrawal_minimum_balance_floor_raises`
  - `test_create_pending_transfer_minimum_balance_floor_raises` (create a valid recipient user first)
  - `test_create_pending_bill_payment_minimum_balance_floor_raises`
- [X] T054 [US3] Make 5 changes to `banking/tests/test_services.py` for `approve_business_pending`:
  - Change `make_business_with_balance` default from `Decimal("5000.00")` → `Decimal("8000.00")` (old default causes auto-rejection once T060 adds the floor guard)
  - In `test_approve_business_pending_updates_business_account_balance`: change explicit `Decimal("5000.00")` → `Decimal("8000.00")`; update assertion from `Decimal("4000.00")` → `Decimal("7000.00")` (8000 − 1000 = 7000, exactly at inclusive floor)
  - Rename `test_approve_business_pending_insufficient_funds_leaves_status_pending` → `test_approve_business_pending_auto_rejects_when_floor_breached`; remove `pytest.raises(InsufficientFundsError)` context manager; add `result = approve_business_pending(pt, auth_user)`; assert `result is False` and `pt.status == PendingTransaction.REJECTED`
  - Add `test_approve_business_pending_returns_true_on_success`: `make_business_with_balance(Decimal("8000.00"))`, pending withdrawal `Decimal("100.00")` (leaves 7900 ≥ 7000), assert result is True and `pt.status == PendingTransaction.APPROVED`
  - Add `test_approve_business_pending_auto_rejects_records_business_transaction`: `make_business()` (balance=0), pending withdrawal `Decimal("9999.00")`, call `approve_business_pending(pt, auth_user)`, assert `BusinessTransaction.objects.filter(business_account=ba, transaction_type=BusinessTransaction.REJECTED).exists()`

### Implementation for Phase 6

- [X] T055 [US1] Update `create_business_account_mock` in `banking/services.py`:
  - Add `initial_deposit: Decimal` as a required parameter after `postal_code`
  - Add guard at function start: `if initial_deposit < Decimal("7000.00"): raise BankingError("Initial deposit must be at least 7,000.")`
  - Add `balance=initial_deposit` to the `BusinessAccount.objects.create(...)` call
  - After BA creation add `BusinessTransaction.objects.create(business_account=business_account, transaction_type=BusinessTransaction.DEPOSIT, amount=initial_deposit, balance_after=initial_deposit)` (still inside `@transaction.atomic`)
- [X] T056 [P] [US1] Add `initial_deposit = forms.DecimalField(min_value=Decimal("7000.00"), max_digits=12, decimal_places=2, label="Initial Deposit")` to `BusinessCreateForm` in `banking/forms.py` (`Decimal` already imported at line 2)
- [X] T057 [US1] Pass `initial_deposit=form.cleaned_data["initial_deposit"]` to `create_business_account_mock(...)` in `create_business_account_view` in `banking/views.py`
- [X] T058 [P] [US1] Insert `initial_deposit` label + input + errors block before the submit button in `banking/templates/banking/create_business_account.html`:
  ```html
  <label for="{{ form.initial_deposit.id_for_label }}">{{ form.initial_deposit.label }}</label>
  {{ form.initial_deposit }} {{ form.initial_deposit.errors }}
  ```
- [X] T059 [US2] In `banking/services.py`, update the balance guard in all 3 `create_pending_*` functions (`create_pending_withdrawal`, `create_pending_transfer`, `create_pending_bill_payment`): replace `if ba.balance < amount:` with `if ba.balance - amount < Decimal("7000.00"):` and update the error message to `"Transaction would bring balance below minimum (7,000)."`
- [X] T060 [US3] Update `approve_business_pending` in `banking/services.py`:
  - Change return annotation from `-> None` to `-> bool`
  - Replace `if ba.balance < pt.amount: raise InsufficientFundsError("Insufficient funds.")` with:
    ```python
    if ba.balance - pt.amount < Decimal("7000.00"):
        reject_business_pending(pending_tx, decided_by)
        return False
    ```
  - Add `return True` as the final statement after the `BusinessTransaction.objects.create(...)` call
- [X] T061 [US3] Update `approve_transaction_view` in `banking/views.py`:
  - Capture `result = approve_business_pending(pending_tx, request.user)` (was a bare call)
  - Replace single `messages.success(request, "Transaction approved and executed.")` with `if result: messages.success(request, "Transaction approved and executed.") else: messages.error(request, "Transaction automatically rejected: minimum balance would be breached.")`
  - Remove the `except BankingError as exc:` block — auto-rejection no longer raises; no other `BankingError` subtype is raised from `approve_business_pending` after T060
- [X] T062 [P] [US3] Update `approve_transaction` tool in `mcp_server/server.py`:
  - Change `services.approve_business_pending(pt, decided_by)` to `result = services.approve_business_pending(pt, decided_by)`
  - Remove the `except services.BankingError as exc: return {"error": str(exc)}` block that wraps the approve call
  - After the call, add `if not result: return {"status": "AUTO_REJECTED", "reason": "minimum balance breach"}`
  - Keep the existing `ba = BusinessAccount.objects.get(...); return {"status": "APPROVED", "business_new_balance": str(ba.balance)}` for the True path

### Final Verification for Phase 6

- [X] T063 Run `python manage.py test banking` — all tests GREEN including new T050–T054 tests; no regressions in US2/US3 existing tests
- [ ] T064 [P] Manually validate the new quickstart.md Validation Checks rows: "Initial deposit below 7,000" (form error), "Withdrawal that would bring balance below 7,000" (error, no pending tx), "Authoriser approves tx that would breach floor" (auto-rejected, flash error, balance unchanged)

**Checkpoint**: Full test suite green; all 10 quickstart.md Validation Checks pass; MCP `approve_transaction` returns `{"status": "AUTO_REJECTED", ...}` on floor breach.

---

## Phase 7: Revised Role Model — Authoriser Dashboard & Direct Transactions (FR-008a, FR-005)

**Goal**: Authoriser logs in and sees a business account dashboard (BA balance, transaction history, transaction forms). Outgoing transactions submitted by the authoriser execute immediately — no pending queue entry created.

**Independent Test**: Log in as authoriser, submit a withdrawal, confirm balance immediately decreases and no `PendingTransaction` row was created.

### Tests for Phase 7 — Write FIRST, verify FAIL before implementing T067–T076 (Constitution §II)

> **NOTE: Write these tests FIRST. Run `pytest banking/tests/` to confirm RED before T067.**

- [X] T065 [P] [US4] Write service tests in banking/tests/test_services.py: `test_withdraw_from_business_deducts_balance_and_creates_transaction`, `test_withdraw_from_business_zero_amount_raises`, `test_withdraw_from_business_floor_breach_raises`, `test_withdraw_from_business_exact_floor_succeeds` (balance − amount == 7000 is acceptable), `test_transfer_from_business_executes_immediately_and_creates_transaction`, `test_transfer_from_business_recipient_not_found_raises`, `test_transfer_from_business_floor_breach_raises`, `test_pay_bill_from_business_creates_transaction_with_description`, `test_pay_bill_from_business_floor_breach_raises`
- [X] T066 [P] [US4] Write view tests in banking/tests/test_views.py: `test_dashboard_view_as_authoriser_shows_business_account`, `test_deposit_view_as_authoriser_updates_balance_immediately`, `test_withdraw_view_as_authoriser_deducts_balance_immediately_no_pending_tx_created`, `test_withdraw_view_as_authoriser_floor_breach_shows_error`, `test_transfer_view_as_authoriser_executes_immediately`, `test_pay_bill_view_as_authoriser_executes_immediately`

### Implementation for Phase 7

- [X] T067 [US4] Add `withdraw_from_business(ba, amount)` to banking/services.py wrapped in `@transaction.atomic`: `_validate_amount(amount)`; re-fetch BA with `select_for_update`; if `ba.balance - amount < Decimal("7000.00")` raise `InsufficientFundsError("Transaction would bring balance below minimum (7,000).")`; deduct from `ba.balance`; `ba.save(update_fields=["balance"])`; create `BusinessTransaction(WITHDRAWAL, amount, balance_after=ba.balance)`
- [X] T068 [P] [US4] Add `transfer_from_business(ba, amount, recipient_phone)` to banking/services.py wrapped in `@transaction.atomic`: `_validate_amount(amount)`; re-fetch BA with `select_for_update`; check floor; look up `Account` by `user__phone_number=recipient_phone` (raise `RecipientNotFoundError` if not found); deduct from ba; add to recipient personal account; save both; create `BusinessTransaction(TRANSFER_OUT, amount, balance_after, counterparty=recipient_account)`; create recipient `Transaction(TRANSFER_IN, amount, balance_after, counterparty=ba.manager.business_account)` — use `Account.objects.get(user__phone_number=recipient_phone)` and the existing personal `transfer()` logic as a reference
- [X] T069 [P] [US4] Add `pay_bill_from_business(ba, amount, category, reference)` to banking/services.py wrapped in `@transaction.atomic`: `_validate_amount(amount)`; re-fetch BA with `select_for_update`; check floor; deduct from ba; `ba.save(update_fields=["balance"])`; create `BusinessTransaction(BILL_PAYMENT, amount, balance_after=ba.balance, description=f"{category} ({reference})")`
- [X] T075 [US4] Add `withdraw_from_business`, `transfer_from_business`, `pay_bill_from_business` to the import block in banking/views.py (alongside existing `.services` imports)
- [X] T070 [US4] Add authoriser branch to `dashboard_view` in banking/views.py: insert `elif hasattr(request.user, "authoriser_profile"):` block (after the manager branch, before personal fallthrough); fetch BA via `request.user.authoriser_profile.business_account`; pass `is_authoriser=True`, `business_account`, `balance=ba.balance`, `recent_transactions=ba.transactions.order_by("-timestamp")[:5]`, `deposit_form`, `withdraw_form`, `transfer_form`, `bill_pay_form=BusinessBillPaymentForm()`; render `banking/dashboard.html`
- [X] T071 [US4] Add authoriser branch to `deposit_view` in banking/views.py: insert `elif hasattr(request.user, "authoriser_profile"):` block; validate `DepositForm`; call `deposit_to_business(ba, amount)` (deposit executes immediately for both roles — same service call as manager); on success flash and redirect to dashboard; on error re-render with authoriser context
- [X] T072 [US4] Add authoriser branch to `withdraw_view` in banking/views.py: insert `elif hasattr(request.user, "authoriser_profile"):` block; call `withdraw_from_business(ba, amount)` (immediate, NOT pending queue); on `InsufficientFundsError` add form error and re-render; on success flash and redirect to dashboard
- [X] T073 [US4] Add authoriser branch to `transfer_view` in banking/views.py: insert `elif hasattr(request.user, "authoriser_profile"):` block; call `transfer_from_business(ba, amount, recipient_phone)`; handle `RecipientNotFoundError` (non-field error) and `InsufficientFundsError` (amount field error); on success flash and redirect
- [X] T074 [US4] Add authoriser branch to `pay_bill_view` in banking/views.py: insert `elif hasattr(request.user, "authoriser_profile"):` block; parse `BusinessBillPaymentForm(request.POST)`; call `pay_bill_from_business(ba, amount, category, reference)`; handle errors; redirect to dashboard on success
- [X] T076 [US4] Update banking/templates/banking/dashboard.html: add `{% elif is_authoriser %}` block (between manager `{% if is_manager %}` and personal `{% else %}`) rendering BA company name, balance, last 5 `BusinessTransaction` records, and inline deposit/withdraw/transfer/bill-pay forms; also add `{% if authoriser_pending_count > 0 %}<a href="{% url 'banking:authoriser_queue' %}">Pending Approvals ({{ authoriser_pending_count }})</a>{% endif %}` inside the authoriser block (FR-009a)

**Checkpoint**: All T065/T066 tests pass; manually follow quickstart Flow 6 — authoriser's withdrawal executes immediately, balance decreases, no `PendingTransaction` row created

---

## Phase 8: Manager Read-Only Pending Queue (FR-009)

**Goal**: Account manager can view all pending transactions for their business account at `/banking/pending/`. View is entirely read-only — no approve or reject buttons. Non-managers get 403. Manager POSTing to the authoriser approve/reject endpoint gets 403.

**Independent Test**: As account manager, submit a withdrawal, then visit `/banking/pending/` — transaction appears in the list with no action controls; attempt `POST /banking/authorise/<id>/approve/` as the manager → 403 returned.

### Tests for Phase 8 — Write FIRST, verify FAIL before implementing T078–T082 (Constitution §II)

> **NOTE: Write these tests FIRST. Run `pytest banking/tests/` to confirm RED before T078.**

- [X] T077 [US5] Write view tests in banking/tests/test_views.py: `test_manager_pending_view_lists_pending_transactions`, `test_manager_pending_view_has_no_approve_reject_controls`, `test_manager_pending_view_empty_queue_shows_message`, `test_manager_pending_view_non_manager_returns_403`, `test_manager_pending_view_unauthenticated_redirects_to_login`

### Implementation for Phase 8

- [X] T078 [US5] Implement `manager_pending_view` in banking/views.py: `@login_required`; GET only (no `@require_POST`); if `not hasattr(request.user, "manager_profile")` return `HttpResponseForbidden()`; filter `PendingTransaction.objects.filter(business_account=request.user.manager_profile.business_account, status=PendingTransaction.PENDING).order_by("-created_at")`; render `banking/manager_pending.html` with `{"pending_txns": pending_txns}`
- [X] T079 [US5] Create banking/templates/banking/manager_pending.html: page heading "Pending Transactions"; table listing each pending transaction (type display, amount, description, `created_at`); empty-queue message when `pending_txns` is empty; navigation link back to dashboard; no approve or reject form controls anywhere on the page
- [X] T080 [US5] Add `path("banking/pending/", manager_pending_view, name="manager_pending")` to banking/urls.py and add `manager_pending_view` to the import from `banking.views`
- [X] T082 [P] [US5] Update banking/templates/banking/authoriser_queue.html: add company name and current balance in the page header above the transactions table; pass `business_account` from `authoriser_queue_view` in banking/views.py — add `"business_account": business_account` to the context dict in that view

### Final Verification for Phase 8

- [X] T083 Run `pytest` — all Phase 7 and Phase 8 tests pass; no regressions in any earlier phase
- [ ] T084 [P] Manually run quickstart.md Flows 6 and 7 and the three new Validation Checks: authoriser floor breach (error, no transaction), non-manager at `/banking/pending/` (403), manager POST to approve/reject endpoint (403)

**Checkpoint**: Full test suite green; all quickstart.md Flows 1–7 and all Validation Checks rows pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** (Setup/Cleanup): No dependencies — start immediately
- **Phase 2** (Foundational): Depends on Phase 1 — BLOCKS all user story phases
- **Phase 3** (US1): Depends on Phase 2 (migration applied)
- **Phase 4** (US2): Depends on Phase 2; practically requires US1 complete (manager users are created by US1's service and needed for test fixtures)
- **Phase 5** (US3): Depends on Phase 2; requires US1 (authoriser user) and US2 (pending transactions to act on)
- **Phase N** (Polish): Depends on all story phases complete
- **Phase 7** (US4 — Authoriser Direct Transactions): Depends on Phases 1–5 complete (authoriser user, service layer, and views must be in place)
- **Phase 8** (US5 — Manager Pending Queue): Depends on Phase 4 (manager view pattern); can proceed in parallel with Phase 7

### User Story Dependencies

- **US1** (Create Business Account): Independently testable after Phase 2; delivers manager + authoriser users needed by US2/US3 tests
- **US2** (Manager Submits Transaction): Requires US1 for fixture setup; PendingTransactions created here are acted on in US3
- **US3** (Authoriser Approves/Rejects): Requires US1 (authoriser user) and US2 (pending transactions)
- **US4** (Authoriser Direct Transactions): Requires US1 (authoriser user created) and existing service/view layer from Phases 4–6; same authoriser fixture as US3
- **US5** (Manager Read-Only Queue): Requires US2 (pending transactions to list); independent of US4

### Within Each Phase

- **Write tests FIRST** — run them and confirm they FAIL before writing implementation (Constitution §II, NON-NEGOTIABLE)
- Models before services (services import models)
- Services before views (views call services)
- Views before templates (templates render view context)
- Tasks marked [P] within a phase can proceed in parallel

### Parallel Opportunities

- T002, T003, T004 (Phase 1 deletions) — different files, run in parallel
- T007, T008, T009 (Phase 2 new models) — different model classes, run in parallel
- T015, T016 (US1 tests) — run in parallel
- T021, T022 (US1 templates) — different template files, run in parallel
- T024, T025 (US2 tests) — run in parallel
- T035, T036, T037 (US3 tests) — run in parallel
- T065, T066 (Phase 7 tests) — service tests and view tests; write in parallel
- T068, T069 (Phase 7 service functions) — different functions; run after T067 establishes the pattern
- Phase 7 (US4) and Phase 8 (US5) can be worked in parallel once Phases 1–5 are complete (different views, templates, and URLs)

---

## Parallel Example: User Story 1

```bash
# Write tests in parallel (coordinate on same test file to avoid conflicts):
T015: Service tests for create_business_account_mock
T016: View tests for create_business_account_view and business_account_created_view

# Verify tests FAIL, then implement in sequence:
T017 (service) → T018 (form) → T019/T020 (views) → T023 (URLs)
T021, T022 (templates) can run in parallel alongside T017
```

---

## Implementation Strategy

### MVP First (Phase 1 + 2 + US1 Only)

1. Complete Phase 1: Remove wrong model code
2. Complete Phase 2: Apply correct migration
3. Complete Phase 3: US1 — business account creation + credential display
4. **STOP and VALIDATE**: Follow quickstart Flow 1; credentials shown once, both users can log in
5. Demo-ready for creation flow

### Incremental Delivery

1. Phase 1 + 2 → Clean foundation, migration applied
2. Add US1 → Business account creation works end-to-end (quickstart Flow 1)
3. Add US2 → Manager submits transactions (quickstart Flows 2 + 3)
4. Add US3 → Authoriser approves/rejects (quickstart Flows 4 + 5)
5. Polish + Phase 6 → All 10 Validation Checks pass, full test suite green
6. Add US4 → Authoriser dashboard + direct transactions (quickstart Flow 6)
7. Add US5 → Manager read-only pending queue (quickstart Flow 7)

---

## Notes

- [P] tasks = different files or independent sections; no cross-task dependencies within the phase
- [Story] label maps each task to its user story for traceability
- **Tests MUST be written and confirmed failing before implementation** (Constitution §II)
- All balance mutations wrapped in `@transaction.atomic`
- `select_for_update` not required at SQLite3 prototype tier
- Personal account flows (Account, Transaction, Biller, personal views) must remain unchanged throughout — run personal account tests after each phase to catch regressions
- Run `python manage.py check` after Phase 1 and after Phase 2 to catch import/model errors early

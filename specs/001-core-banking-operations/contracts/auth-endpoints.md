# Authentication Endpoint Contracts

Branch: `001-core-banking-operations` | Generated: 2026-05-21

All endpoints render server-side HTML. All POST endpoints require a valid Django
CSRF token (`csrfmiddlewaretoken` form field or `X-CSRFToken` header).

URL prefix: `/accounts/`

---

## GET `/accounts/signup/`

Renders the registration form.

**Auth required**: No
**Template**: `accounts/signup.html`

---

## POST `/accounts/signup/`

Processes new user registration.

**Auth required**: No

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `name` | CharField | Required; max 150 chars |
| `username` | CharField | Required; max 150 chars; case-insensitive unique (FR-002) |
| `email` | EmailField | Required; unique; stored lowercase (FR-002) |
| `phone_number` | CharField | Required; matches `^[89]\d{7}$` after normalization; unique (FR-028, FR-002) |
| `password1` | CharField | Required; meets Django password strength rules (FR-003) |
| `password2` | CharField | Required; must match `password1` |

**On success**: Redirect to `/accounts/login/`; flash "Account created — please
log in."

**On failure**: Re-render `accounts/signup.html` with inline field errors.

**Rejection reasons** (FR-002):
- Username already taken (case-insensitive)
- Email already registered
- Phone number already registered
- Password too weak (too short, too common, entirely numeric)
- Passwords do not match

---

## GET `/accounts/login/`

Renders the login form.

**Auth required**: No
**Template**: `accounts/login.html`

---

## POST `/accounts/login/`

Authenticates the user and starts a session.

**Auth required**: No

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `username` | CharField | Required |
| `password` | CharField | Required |

**On success** (FR-004, FR-006): Create session; redirect to `/dashboard/`.

**On failure** (FR-005): Re-render `accounts/login.html` with a single generic
error — "Invalid username or password." — without revealing which field was wrong.

---

## POST `/accounts/logout/`

Ends the current session.

**Auth required**: Yes (`@login_required`)

**On success** (FR-006): Invalidate session; redirect to `/accounts/login/`.

---

## GET `/accounts/password-reset/`

Renders the reset-request form.

**Auth required**: No
**Template**: `accounts/password_reset.html`

---

## POST `/accounts/password-reset/`

Accepts an email address and, if a matching account exists, sends a single-use
reset link.

**Auth required**: No

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `email` | EmailField | Required; valid email format |

**Response** (FR-029): Always renders `accounts/password_reset_done.html` with
"If an account exists for that email address, a reset link has been sent."
The response is identical whether or not the email is registered.

**When email matches an account** (FR-030): Send email containing a single-use,
time-limited (1 hour) reset link to that address.

---

## GET `/accounts/password-reset/confirm/<uidb64>/<token>/`

Renders the new-password form if the token is valid.

**Auth required**: No
**Template (valid token)**: `accounts/password_reset_confirm.html`
**Template (invalid/expired token)**: `accounts/password_reset_confirm.html`
with `validlink=False` context variable shown as an error page (FR-031)

---

## POST `/accounts/password-reset/confirm/<uidb64>/<token>/`

Sets the new password if the token is valid and unexpired.

**Auth required**: No

**Form fields**:

| Field | Type | Validation |
|-------|------|------------|
| `new_password1` | CharField | Required; meets Django password strength rules (FR-031) |
| `new_password2` | CharField | Required; must match `new_password1` |

**On success** (FR-031, FR-032):
- Password updated
- Token invalidated (cannot be reused)
- All other active sessions for that account ended
- Redirect to `/accounts/password-reset/complete/`

**On failure**: Re-render form with errors, or error page for
expired/invalid/already-used tokens.

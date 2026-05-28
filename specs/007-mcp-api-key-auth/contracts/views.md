# Web View Contracts: Account API Keys

All views require an authenticated interactive user session. API keys are managed for the
current user only.

## `GET /accounts/api-keys/`

Lists the current user's API keys without exposing full secrets.

### Response expectations

- Status `200`.
- Shows each key's name, identifier, status, created date, last-used date when available,
  and revoked date when applicable.
- Does not include any full API key secret.
- Includes a create-key form.
- Includes revoke controls for active keys only.

## `POST /accounts/api-keys/`

Creates a new API key for the current user after identity confirmation.

### Form fields

| Field | Required | Validation |
|---|---|---|
| `name` | yes | Trimmed, non-empty, max 80 characters, unique among active keys for this user |
| `password` | yes | Must match the current user's account password |

### Success

- Creates the key.
- Records a non-sensitive `CREATED` audit event.
- Returns a success page or response that displays the full API key secret exactly once.

### Validation errors

| Condition | Expected behavior |
|---|---|
| Missing or blank name | Re-render form with field error; no key created |
| Duplicate active key name for user | Re-render form with field error; no key created |
| Active key limit reached | Re-render form with clear limit error; no key created |
| Wrong password | Re-render form with generic confirmation error; no key created |

## One-time secret display

The full secret is available only in the immediate response after successful creation.
Refreshing or returning to the key list must not recover the full secret. If the user loses
the secret, they must create a replacement key and revoke the old key.

## `POST /accounts/api-keys/<identifier>/revoke/`

Revokes one active API key owned by the current user.

### Success

- Sets the key's revoked date.
- Records a non-sensitive `REVOKED` audit event.
- Redirects back to the key list with a confirmation message.
- Future MCP authentication with that key fails immediately.

### Error cases

| Condition | Expected behavior |
|---|---|
| Identifier not found for current user | Return `404` |
| Key already revoked | Redirect to list with an informational message; no second revocation event required |
| Key belongs to another user | Return `404`; do not reveal that the key exists |

## Navigation

The account profile area should provide a clear route to API key management. The API key
management page should provide a clear route back to the user's profile.

# MCP Tool Contract: API Key Authentication

All MCP tools communicate via JSON-RPC over stdio through the existing FastMCP server.
Errors return a structured object:

```json
{"error": "<human-readable message>"}
```

The existing `login(username, password)` tool remains available and unchanged.

## `login_with_api_key`

Authenticates an MCP client with a user-generated API key and returns a short-lived
session token for protected MCP write tools.

### Input

| Field | Type | Required | Description |
|---|---|---|---|
| `api_key` | string | yes | Full API key secret shown once during key creation |

### Success output

```json
{
  "session_token": "<64-char hex token>",
  "expires_in_minutes": 15,
  "username": "alice",
  "auth_method": "api_key",
  "api_key_identifier": "ak_2f4c9a1b"
}
```

### Error cases

| Condition | Message |
|---|---|
| Empty key | `"Authentication failed."` |
| Malformed key | `"Authentication failed."` |
| Unknown key | `"Authentication failed."` |
| Secret mismatch | `"Authentication failed."` |
| Revoked key | `"Authentication failed."` |

The error message is intentionally generic and must not reveal whether a key identifier
exists.

## Protected tool compatibility

All existing protected write tools continue to accept `session_token` exactly as before.
A token returned by `login_with_api_key` must be accepted anywhere a token returned by
`login` is accepted, subject to the same owner and role checks.

### Compatibility examples

```json
{
  "tool": "deposit_funds",
  "arguments": {
    "username": "alice",
    "amount": "100.00",
    "session_token": "<token from login_with_api_key>"
  }
}
```

```json
{
  "tool": "approve_transaction",
  "arguments": {
    "pending_transaction_id": 42,
    "session_token": "<authoriser token from login_with_api_key>"
  }
}
```

## Revoked-key session behavior

If a session token was issued by `login_with_api_key` and the underlying API key has since
been revoked, protected tool calls using that session token return:

```json
{"error": "Session expired or invalid. Please log in again."}
```

No protected operation may execute after this validation failure.

"""Absence tests for removed business MCP tools."""


def test_business_mcp_tools_are_not_exported():
    import mcp_server.server as server

    removed = [
        "get_business_account",
        "list_business_transactions",
        "list_pending_transactions",
        "approve_transaction",
        "reject_transaction",
        "create_business_account",
    ]
    for name in removed:
        assert not hasattr(server, name)


def test_username_password_login_is_not_exported():
    import mcp_server.server as server

    assert not hasattr(server, "login")

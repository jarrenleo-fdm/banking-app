"""MCP-layer validation helpers."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


def _mcp_validate_amount(amount: str) -> Decimal:
    """Parse and validate an amount string: must be positive with ≤2 decimal places."""
    try:
        value = Decimal(amount)
    except InvalidOperation:
        raise ValueError(f"Invalid amount: {amount!r}. Must be a numeric string.")
    if value <= 0:
        raise ValueError("Amount must be positive.")
    if value != value.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN):
        raise ValueError("Amount must have at most 2 decimal places.")
    return value

"""MCP-layer validation helpers."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN


_CENT = Decimal("0.01")


def _parse_decimal(amount: str, error_message: str) -> Decimal:
    try:
        value = Decimal(str(amount).strip())
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(error_message) from exc
    if not value.is_finite():
        raise ValueError(error_message)
    return value


def _has_cent_precision(value: Decimal) -> bool:
    return value == value.quantize(_CENT, rounding=ROUND_HALF_EVEN)


def _mcp_validate_amount(amount: str) -> Decimal:
    """Parse and validate an amount string: must be positive with ≤2 decimal places."""
    value = _parse_decimal(
        amount,
        f"Invalid amount: {amount!r}. Must be a numeric string.",
    )
    if value <= 0:
        raise ValueError("Amount must be positive.")
    if not _has_cent_precision(value):
        raise ValueError("Amount must have at most 2 decimal places.")
    return value


def _mcp_validate_initial_deposit(amount: str | None) -> Decimal:
    """Parse an optional signup initial deposit, allowing zero but not negatives."""
    if amount in (None, ""):
        return Decimal("0.00")

    value = _parse_decimal(amount, "Invalid amount.")
    if value < 0:
        raise ValueError("Amount must be greater than or equal to zero.")
    if not _has_cent_precision(value):
        raise ValueError("Amount must have at most 2 decimal places.")
    return value

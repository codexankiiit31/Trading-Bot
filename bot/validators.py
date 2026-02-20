"""
validators.py
-------------
Pure validation functions for CLI inputs.
Raises ValueError with clear messages on invalid input.
"""

from __future__ import annotations

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


def validate_symbol(symbol: str) -> str:
    """
    Symbols must be non-empty alphanumeric strings (e.g. BTCUSDT).
    Returns the uppercased symbol.
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol cannot be empty.")
    cleaned = symbol.strip().upper()
    if not cleaned.isalnum():
        raise ValueError(
            f"Invalid symbol '{cleaned}'. "
            "Symbols must be alphanumeric (e.g. BTCUSDT, ETHUSDT)."
        )
    return cleaned


def validate_side(side: str) -> str:
    """
    Side must be BUY or SELL (case-insensitive).
    Returns uppercased side.
    """
    if not side or not side.strip():
        raise ValueError("Side cannot be empty.")
    cleaned = side.strip().upper()
    if cleaned not in VALID_SIDES:
        raise ValueError(
            f"Invalid side '{cleaned}'. Must be one of: {', '.join(sorted(VALID_SIDES))}."
        )
    return cleaned


def validate_order_type(order_type: str) -> str:
    """
    Order type must be MARKET or LIMIT (case-insensitive).
    Returns uppercased order type.
    """
    if not order_type or not order_type.strip():
        raise ValueError("Order type cannot be empty.")
    cleaned = order_type.strip().upper()
    if cleaned not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Invalid order type '{cleaned}'. "
            f"Must be one of: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return cleaned


def validate_quantity(quantity: str | float) -> float:
    """
    Quantity must be a positive number.
    Returns a float.
    """
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid quantity '{quantity}'. Must be a positive number (e.g. 0.01)."
        )
    if qty <= 0:
        raise ValueError(
            f"Quantity must be greater than zero, got {qty}."
        )
    return qty


def validate_price(price: str | float | None, order_type: str) -> float | None:
    """
    Price is required and must be positive for LIMIT orders.
    For MARKET orders, price is ignored (returns None).
    """
    order_type = order_type.strip().upper()

    if order_type == "MARKET":
        if price is not None:
            # Inform but don't block — price is silently ignored for market orders
            pass
        return None

    # LIMIT order — price is required
    if price is None:
        raise ValueError(
            "Price is required for LIMIT orders. "
            "Use --price <value> (e.g. --price 30000)."
        )
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid price '{price}'. Must be a positive number (e.g. 30000.50)."
        )
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p

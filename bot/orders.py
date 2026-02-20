"""
orders.py
---------
Order orchestration layer.

Responsibilities:
  - Run input validation
  - Call BinanceClient to place the order
  - Format and print a clear summary to stdout
  - Log the full lifecycle
"""

from __future__ import annotations

from typing import Any

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import get_logger
from bot.validators import (
    validate_order_type,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)

logger = get_logger(__name__)


def _print_separator(char: str = "─", width: int = 60) -> None:
    print(char * width)


def _print_order_summary(
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float | None,
) -> None:
    """Print the order request summary before sending."""
    _print_separator()
    print("  ORDER REQUEST SUMMARY")
    _print_separator()
    print(f"  Symbol     : {symbol}")
    print(f"  Side       : {side}")
    print(f"  Type       : {order_type}")
    print(f"  Quantity   : {quantity}")
    if price is not None:
        print(f"  Price      : {price}")
    else:
        print("  Price      : (market price)")
    _print_separator()
    print()


def _print_order_response(response: dict[str, Any]) -> None:
    """Print key fields from the Binance order response."""
    _print_separator()
    print("  ORDER RESPONSE")
    _print_separator()
    print(f"  Order ID   : {response.get('orderId', 'N/A')}")
    print(f"  Client OID : {response.get('clientOrderId', 'N/A')}")
    print(f"  Symbol     : {response.get('symbol', 'N/A')}")
    print(f"  Side       : {response.get('side', 'N/A')}")
    print(f"  Type       : {response.get('type', 'N/A')}")
    print(f"  Status     : {response.get('status', 'N/A')}")
    print(f"  Orig Qty   : {response.get('origQty', 'N/A')}")
    print(f"  Executed   : {response.get('executedQty', 'N/A')}")

    avg_price = response.get("avgPrice") or response.get("price", "N/A")
    print(f"  Avg Price  : {avg_price}")
    print(f"  Time       : {response.get('updateTime', 'N/A')}")
    _print_separator()


def place_order(
    client: BinanceClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: str | float,
    price: str | float | None = None,
) -> dict[str, Any]:
    """
    Validate inputs, place the order via the client, and display results.

    Parameters
    ----------
    client     : Authenticated BinanceClient instance
    symbol     : Trading pair (e.g. 'BTCUSDT')
    side       : 'BUY' or 'SELL'
    order_type : 'MARKET' or 'LIMIT'
    quantity   : Order quantity (str or float)
    price      : Order price — required for LIMIT, ignored for MARKET

    Returns
    -------
    Parsed order response dict.

    Raises
    ------
    ValueError       : Invalid inputs
    BinanceAPIError  : API-level errors
    """
    # --- Validate all inputs ---
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    qty = validate_quantity(quantity)
    validated_price = validate_price(price, order_type)

    logger.info(
        "Validated order params: symbol=%s side=%s type=%s qty=%s price=%s",
        symbol, side, order_type, qty, validated_price,
    )

    # --- Print request summary ---
    _print_order_summary(symbol, side, order_type, qty, validated_price)

    # --- Send order ---
    try:
        response = client.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=qty,
            price=validated_price,
        )
    except BinanceAPIError as exc:
        logger.error("Order failed — BinanceAPIError: %s", exc)
        _print_separator("═")
        print(f"  ✗ ORDER FAILED")
        print(f"  Error Code : {exc.code}")
        print(f"  Message    : {exc.message}")
        _print_separator("═")
        raise
    except Exception as exc:
        logger.error("Order failed — unexpected error: %s", exc)
        _print_separator("═")
        print(f"  ✗ ORDER FAILED — {exc}")
        _print_separator("═")
        raise

    # --- Print response ---
    _print_order_response(response)
    logger.info("Order placed successfully: orderId=%s status=%s",
                response.get("orderId"), response.get("status"))

    print(f"  ✔ ORDER PLACED SUCCESSFULLY")
    _print_separator("═")
    print()

    return response

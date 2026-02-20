"""
cli.py
------
Command-line entry point for the Binance Futures Testnet Trading Bot.

Usage — Place an order
-----
  python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.002
  python cli.py --symbol BTCUSDT --side SELL --order-type LIMIT --quantity 0.002 --price 99999

Usage — View orders
-----
  python cli.py --symbol BTCUSDT --list-orders
  python cli.py --symbol BTCUSDT --list-orders --limit 5
  python cli.py --symbol BTCUSDT --query-order 12412093428

API credentials can be supplied via:
  1. .env file (recommended):  BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET
  2. CLI flags:                 --api-key <key> --api-secret <secret>
"""

import argparse
import datetime
import os
import sys

from dotenv import load_dotenv
load_dotenv()  # Loads .env file from the project root automatically

from bot.client import BinanceClient, BinanceAPIError
from bot.logging_config import setup_logging, get_logger
from bot.orders import place_order

# Initialise logging before anything else
setup_logging()
logger = get_logger(__name__)

SEP  = "─" * 60
SEP2 = "═" * 60


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_ts(ms: int) -> str:
    """Convert a millisecond Unix timestamp to a readable datetime string."""
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ms)


def _print_order(order: dict) -> None:
    """Pretty-print a single order dict."""
    print(SEP)
    print(f"  Order ID   : {order.get('orderId', 'N/A')}")
    print(f"  Symbol     : {order.get('symbol', 'N/A')}")
    print(f"  Side       : {order.get('side', 'N/A')}")
    print(f"  Type       : {order.get('type', 'N/A')}")
    print(f"  Status     : {order.get('status', 'N/A')}")
    print(f"  Orig Qty   : {order.get('origQty', 'N/A')}")
    print(f"  Executed   : {order.get('executedQty', 'N/A')}")
    avg = order.get('avgPrice') or order.get('price', '0.00')
    print(f"  Avg Price  : {avg}")
    print(f"  Time       : {_fmt_ts(order['time'])}" if 'time' in order else "")
    print(SEP)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet Trading Bot\n"
            "Place and query MARKET or LIMIT orders on USDT-M Futures Testnet."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Place orders\n"
            "  python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.002\n"
            "  python cli.py --symbol ETHUSDT --side SELL --order-type LIMIT --quantity 0.05 --price 3500\n\n"
            "  # View orders\n"
            "  python cli.py --symbol BTCUSDT --list-orders\n"
            "  python cli.py --symbol BTCUSDT --list-orders --limit 5\n"
            "  python cli.py --symbol BTCUSDT --query-order 12412093428\n\n"
            "Env vars (in .env file):\n"
            "  BINANCE_TESTNET_API_KEY\n"
            "  BINANCE_TESTNET_API_SECRET"
        ),
    )

    # --- Symbol (always required) ---
    parser.add_argument(
        "--symbol", "-s",
        required=True,
        metavar="SYMBOL",
        help="Trading pair symbol, e.g. BTCUSDT",
    )

    # --- Query modes ---
    query_group = parser.add_argument_group("Order Query (use instead of placing an order)")
    query_group.add_argument(
        "--list-orders",
        action="store_true",
        dest="list_orders",
        help="List recent orders for --symbol",
    )
    query_group.add_argument(
        "--limit",
        type=int,
        default=10,
        metavar="N",
        help="Number of orders to list (default: 10, max: 1000)",
    )
    query_group.add_argument(
        "--query-order",
        type=int,
        default=None,
        dest="query_order",
        metavar="ORDER_ID",
        help="Query a specific order by its Order ID",
    )

    # --- Order placement parameters ---
    order_group = parser.add_argument_group("Order Placement")
    order_group.add_argument(
        "--side",
        choices=["BUY", "SELL"],
        type=str.upper,
        metavar="SIDE",
        help="Order side: BUY or SELL",
    )
    order_group.add_argument(
        "--order-type", "-t",
        dest="order_type",
        choices=["MARKET", "LIMIT"],
        type=str.upper,
        metavar="TYPE",
        help="Order type: MARKET or LIMIT",
    )
    order_group.add_argument(
        "--quantity", "-q",
        metavar="QTY",
        help="Order quantity (e.g. 0.002)",
    )
    order_group.add_argument(
        "--price", "-p",
        default=None,
        metavar="PRICE",
        help="Limit price — required for LIMIT orders (e.g. 30000)",
    )

    # --- Auth parameters ---
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="Binance Testnet API key (overrides .env / env var)",
    )
    auth_group.add_argument(
        "--api-secret",
        default=None,
        metavar="SECRET",
        help="Binance Testnet API secret (overrides .env / env var)",
    )

    return parser


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # --- Resolve API credentials ---
    api_key = args.api_key or os.environ.get("BINANCE_TESTNET_API_KEY", "")
    api_secret = args.api_secret or os.environ.get("BINANCE_TESTNET_API_SECRET", "")

    if not api_key or not api_secret:
        parser.error(
            "API key and secret are required.\n"
            "  Add them to your .env file, or\n"
            "  set BINANCE_TESTNET_API_KEY / BINANCE_TESTNET_API_SECRET env vars."
        )

    # --- Build client ---
    try:
        client = BinanceClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        logger.error("Client init failed: %s", exc)
        return 1

    # -----------------------------------------------------------------------
    # MODE 1: Query a specific order by ID
    # -----------------------------------------------------------------------
    if args.query_order is not None:
        try:
            order = client.get_order(symbol=args.symbol.upper(), order_id=args.query_order)
            print(f"\n  ORDER DETAILS — ID {args.query_order}")
            _print_order(order)
            return 0
        except BinanceAPIError as exc:
            print(f"\n  ✗ API ERROR: {exc.message}\n", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"\n  ✗ ERROR: {exc}\n", file=sys.stderr)
            return 1

    # -----------------------------------------------------------------------
    # MODE 2: List recent orders
    # -----------------------------------------------------------------------
    if args.list_orders:
        try:
            orders = client.list_orders(symbol=args.symbol.upper(), limit=args.limit)
            if not orders:
                print(f"\n  No orders found for {args.symbol.upper()}.\n")
                return 0
            print(f"\n  RECENT ORDERS — {args.symbol.upper()} (last {len(orders)})")
            for o in orders:
                _print_order(o)
            print(f"  {len(orders)} order(s) shown.\n")
            return 0
        except BinanceAPIError as exc:
            print(f"\n  ✗ API ERROR: {exc.message}\n", file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"\n  ✗ ERROR: {exc}\n", file=sys.stderr)
            return 1

    # -----------------------------------------------------------------------
    # MODE 3: Place an order (default mode)
    # -----------------------------------------------------------------------
    if not args.side or not args.order_type or not args.quantity:
        parser.error(
            "To place an order, --side, --order-type, and --quantity are required.\n"
            "  To view orders instead, use --list-orders or --query-order ORDER_ID"
        )

    try:
        place_order(
            client=client,
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
        )
        return 0

    except ValueError as exc:
        print(f"\n  ✗ VALIDATION ERROR: {exc}\n", file=sys.stderr)
        logger.warning("Validation error: %s", exc)
        return 1

    except BinanceAPIError:
        return 1

    except Exception as exc:
        print(f"\n  ✗ UNEXPECTED ERROR: {exc}\n", file=sys.stderr)
        logger.exception("Unexpected error during order placement")
        return 1


if __name__ == "__main__":
    sys.exit(main())

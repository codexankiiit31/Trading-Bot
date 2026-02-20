"""
client.py
---------
Low-level Binance Futures Testnet REST client.

Handles:
  - HMAC-SHA256 request signing
  - Timestamp injection
  - HTTP request execution
  - Response parsing and error raising
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from typing import Any

import requests

from bot.logging_config import get_logger

logger = get_logger(__name__)

TESTNET_BASE_URL = "https://testnet.binancefuture.com"


class BinanceAPIError(Exception):
    """Raised when the Binance API returns a non-2xx response or an error body."""

    def __init__(self, status_code: int, code: int, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance Error {code}: {message}")


class BinanceClient:
    """
    Thin wrapper around the Binance Futures Testnet REST API.

    Attributes
    ----------
    api_key    : Testnet API key
    api_secret : Testnet API secret (used for signing)
    base_url   : Base URL (default: testnet)
    timeout    : HTTP request timeout in seconds
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = TESTNET_BASE_URL,
        timeout: int = 10,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("API key and secret must not be empty.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"X-MBX-APIKEY": self.api_key})
        self._time_offset_ms: int = 0  # offset = server_time - local_time
        self._sync_server_time()  # sync clock on startup
        logger.debug("BinanceClient initialised with base_url=%s", self.base_url)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _sync_server_time(self) -> None:
        """Fetch Binance server time and compute clock offset to avoid -1021 errors."""
        try:
            url = f"{self.base_url}/fapi/v1/time"
            resp = self._session.get(url, timeout=self.timeout)
            server_time = resp.json()["serverTime"]
            local_time = int(time.time() * 1000)
            self._time_offset_ms = server_time - local_time
            logger.debug("Server time synced. Offset: %dms", self._time_offset_ms)
        except Exception as exc:
            logger.warning("Could not sync server time: %s — using local clock", exc)
            self._time_offset_ms = 0

    def _sign(self, params: dict[str, Any]) -> dict[str, Any]:
        """Inject server-synced timestamp and append HMAC-SHA256 signature to params."""
        params["timestamp"] = int(time.time() * 1000) + self._time_offset_ms
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        signed: bool = False,
        _retries: int = 3,
    ) -> dict[str, Any]:
        """
        Execute an HTTP request and return the parsed JSON body.
        Automatically retries up to _retries times on network errors.

        Raises
        ------
        BinanceAPIError   : API returned an error code
        requests.Timeout  : Request timed out (after all retries)
        requests.ConnectionError : Network failure (after all retries)
        """
        params = params or {}
        if signed:
            params = self._sign(params)

        url = f"{self.base_url}{endpoint}"
        logger.debug("→ %s %s | params=%s", method.upper(), url, params)

        for attempt in range(1, _retries + 1):
            try:
                response = self._session.request(
                    method,
                    url,
                    params=params if method.upper() == "GET" else None,
                    data=params if method.upper() == "POST" else None,
                    timeout=self.timeout,
                )
                break  # success — exit retry loop
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt < _retries:
                    wait = attempt * 2  # 2s, 4s
                    print(f"  ⚠ Network error (attempt {attempt}/{_retries}). Retrying in {wait}s...")
                    logger.warning("Network error attempt %d/%d: %s", attempt, _retries, exc)
                    time.sleep(wait)
                else:
                    logger.error("Network error: %s %s — %s", method, url, exc)
                    raise


        logger.debug("← HTTP %s | body=%s", response.status_code, response.text[:500])

        # Parse JSON
        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response: %s", response.text[:200])
            response.raise_for_status()
            return {}

        # Binance error body (even on 200 sometimes)
        if isinstance(data, dict) and "code" in data and data["code"] < 0:
            logger.error("Binance API error: %s", data)
            raise BinanceAPIError(
                status_code=response.status_code,
                code=data["code"],
                message=data.get("msg", "Unknown error"),
            )

        if not response.ok:
            logger.error("HTTP error %s: %s", response.status_code, data)
            raise BinanceAPIError(
                status_code=response.status_code,
                code=data.get("code", -1),
                message=data.get("msg", response.reason),
            )

        return data

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def get_exchange_info(self, symbol: str) -> dict[str, Any]:
        """
        Fetch exchange info for a specific symbol.
        Used to verify the symbol exists before placing an order.
        """
        logger.debug("Fetching exchange info for symbol=%s", symbol)
        data = self._request("GET", "/fapi/v1/exchangeInfo")
        symbols = {s["symbol"]: s for s in data.get("symbols", [])}
        if symbol not in symbols:
            raise BinanceAPIError(
                status_code=400,
                code=-1121,
                message=f"Invalid symbol '{symbol}'. Not found on Binance Futures Testnet.",
            )
        return symbols[symbol]

    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float | None = None,
    ) -> dict[str, Any]:
        """
        Place a futures order on the testnet.

        Parameters
        ----------
        symbol     : e.g. 'BTCUSDT'
        side       : 'BUY' or 'SELL'
        order_type : 'MARKET' or 'LIMIT'
        quantity   : order quantity
        price      : required for LIMIT orders

        Returns
        -------
        Parsed order response dict from Binance.
        """
        params: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("Price must be provided for LIMIT orders.")
            params["price"] = price
            params["timeInForce"] = "GTC"  # Good Till Cancelled

        logger.info(
            "Placing order: symbol=%s side=%s type=%s qty=%s price=%s",
            symbol, side, order_type, quantity, price,
        )
        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> dict[str, Any]:
        """Query a single order by its Order ID."""
        logger.debug("Querying order: symbol=%s order_id=%s", symbol, order_id)
        return self._request(
            "GET", "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )

    def list_orders(self, symbol: str, limit: int = 10) -> Any:
        """Fetch recent orders for a symbol (default: last 10)."""
        logger.debug("Listing orders: symbol=%s limit=%s", symbol, limit)
        return self._request(
            "GET", "/fapi/v1/allOrders",
            params={"symbol": symbol, "limit": limit},
            signed=True,
        )

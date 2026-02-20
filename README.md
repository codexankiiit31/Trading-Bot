# Binance Futures Testnet Trading Bot

A clean Python CLI application to place **MARKET** and **LIMIT** orders on [Binance Futures USDT-M Testnet](https://testnet.binancefuture.com). Built with direct REST calls + HMAC-SHA256 signing — no Binance SDK required.

---

## Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # package marker
│   ├── client.py            # Binance REST client (signing, HTTP, error handling)
│   ├── orders.py            # order orchestration + output formatting
│   ├── validators.py        # input validation
│   └── logging_config.py   # logging setup (file + console)
├── logs/
│   └── trading_bot.log      # auto-created on first run
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Get Testnet API Credentials

1. Go to [https://testnet.binancefuture.com](https://testnet.binancefuture.com)
2. Sign in with your GitHub account
3. Navigate to **API Key** section → click **Generate**
4. Copy your **API Key** and **Secret Key**

### 2. Create Virtual Environment

```bash
cd trading_bot
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API Credentials (Recommended)

**Option A — Environment variables (preferred):**

```bash
# Windows (CMD)
set BINANCE_TESTNET_API_KEY=your_api_key_here
set BINANCE_TESTNET_API_SECRET=your_api_secret_here

# Windows (PowerShell)
$env:BINANCE_TESTNET_API_KEY="your_api_key_here"
$env:BINANCE_TESTNET_API_SECRET="your_api_secret_here"

# macOS / Linux
export BINANCE_TESTNET_API_KEY=your_api_key_here
export BINANCE_TESTNET_API_SECRET=your_api_secret_here
```

**Option B — CLI flags (less secure):**

Pass `--api-key` and `--api-secret` directly on every command.

---

## Usage

### Command Syntax

```
python cli.py --symbol SYMBOL --side SIDE --order-type TYPE --quantity QTY [--price PRICE]
              [--api-key KEY] [--api-secret SECRET]
```

### Arguments

| Argument | Required | Description |
|---|---|---|
| `--symbol` / `-s` | ✅ | Trading pair, e.g. `BTCUSDT`, `ETHUSDT` |
| `--side` | ✅ | `BUY` or `SELL` |
| `--order-type` / `-t` | ✅ | `MARKET` or `LIMIT` |
| `--quantity` / `-q` | ✅ | Quantity to buy/sell, e.g. `0.001` |
| `--price` / `-p` | ✅ for LIMIT | Limit price, e.g. `30000` |
| `--api-key` | Optional | Overrides env var `BINANCE_TESTNET_API_KEY` |
| `--api-secret` | Optional | Overrides env var `BINANCE_TESTNET_API_SECRET` |

---

## Examples

### Market BUY

```bash
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity 0.001
```

### Market SELL

```bash
python cli.py --symbol ETHUSDT --side SELL --order-type MARKET --quantity 0.01
```

### Limit BUY

```bash
python cli.py --symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.001 --price 30000
```

### Limit SELL (with explicit credentials)

```bash
python cli.py --symbol BTCUSDT --side SELL --order-type LIMIT --quantity 0.001 --price 99999 \
  --api-key YOUR_KEY --api-secret YOUR_SECRET
```

### Help

```bash
python cli.py --help
```

---

## Sample Output

```
────────────────────────────────────────────────────────────
  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────────
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Quantity   : 0.001
  Price      : (market price)
────────────────────────────────────────────────────────────

────────────────────────────────────────────────────────────
  ORDER RESPONSE
────────────────────────────────────────────────────────────
  Order ID   : 3602562068
  Client OID : abc123...
  Symbol     : BTCUSDT
  Side       : BUY
  Type       : MARKET
  Status     : FILLED
  Orig Qty   : 0.001
  Executed   : 0.001
  Avg Price  : 43215.60
  Time       : 1708354564123
────────────────────────────────────────────────────────────
  ✔ ORDER PLACED SUCCESSFULLY
════════════════════════════════════════════════════════════
```

---

## Logging

All API requests, responses, and errors are logged to `logs/trading_bot.log`.

- **Console**: Shows `WARNING` and above only (clean output)
- **Log file**: Full `DEBUG`-level detail — request params, raw response JSON, errors

```bash
# View recent logs (Windows)
type logs\trading_bot.log

# View recent logs (macOS / Linux)
tail -f logs/trading_bot.log
```

---

## Error Handling

| Error Type | Behaviour |
|---|---|
| Missing `--price` for LIMIT | Clear validation error, exit code 1 |
| Invalid symbol / side / type | Clear validation error, exit code 1 |
| Negative or zero quantity / price | Clear validation error, exit code 1 |
| Binance API error (e.g. bad symbol) | Prints error code + message, exit code 1 |
| Network timeout / connection failure | Prints error, exit code 1 |
| Missing API credentials | Argument parser error with instructions |

---

## Running Tests (Validation Only)

These commands test validation logic without requiring API credentials:

```bash
# Missing price for LIMIT order
python cli.py --symbol BTCUSDT --side BUY --order-type LIMIT --quantity 0.001

# Invalid side
python cli.py --symbol BTCUSDT --side FOO --order-type MARKET --quantity 0.001

# Invalid quantity
python cli.py --symbol BTCUSDT --side BUY --order-type MARKET --quantity -5
```

All should print a clear error message and exit with code 1.

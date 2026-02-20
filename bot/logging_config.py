"""
logging_config.py
-----------------
Configures structured logging for the trading bot.

- File handler  : DEBUG+  → logs/trading_bot.log  (rotating, 5 MB × 3 backups)
- Console handler: WARNING+ → stderr (clean, minimal noise)
"""

import logging
import os
from logging.handlers import RotatingFileHandler

_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "trading_bot.log")

_FILE_FMT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
)
_CONSOLE_FMT = "%(levelname)s: %(message)s"

_configured = False


def setup_logging() -> None:
    """
    Initialise root logger. Safe to call multiple times — only configures once.
    """
    global _configured
    if _configured:
        return

    os.makedirs(_LOG_DIR, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # --- File handler (full detail) ---
    fh = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(_FILE_FMT))

    # --- Console handler (warnings + errors only) ---
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter(_CONSOLE_FMT))

    root.addHandler(fh)
    root.addHandler(ch)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger. Always call setup_logging() first.
    """
    setup_logging()
    return logging.getLogger(name)

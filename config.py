from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "trader.db"

# Active markets requested: gold and major forex pairs. No Bitcoin or crypto
# market is included in the active strategy universe.
# Yahoo Finance quotes may be delayed/indicative; gold uses a COMEX futures proxy.
MARKETS = {
    "XAUUSD": {"name": "Gold (COMEX futures proxy)", "provider": "yahoo", "ticker": "GC=F", "quote": "USD/oz"},
    "EURUSD": {"name": "Euro / US Dollar", "provider": "yahoo", "ticker": "EURUSD=X", "quote": "USD"},
    "GBPUSD": {"name": "British Pound / US Dollar", "provider": "yahoo", "ticker": "GBPUSD=X", "quote": "USD"},
    "USDJPY": {"name": "US Dollar / Japanese Yen", "provider": "yahoo", "ticker": "USDJPY=X", "quote": "JPY"},
    "AUDUSD": {"name": "Australian Dollar / US Dollar", "provider": "yahoo", "ticker": "AUDUSD=X", "quote": "USD"},
    "USDCAD": {"name": "US Dollar / Canadian Dollar", "provider": "yahoo", "ticker": "USDCAD=X", "quote": "CAD"},
    "USDCHF": {"name": "US Dollar / Swiss Franc", "provider": "yahoo", "ticker": "USDCHF=X", "quote": "CHF"},
    "NZDUSD": {"name": "New Zealand Dollar / US Dollar", "provider": "yahoo", "ticker": "NZDUSD=X", "quote": "USD"},
}
SYMBOLS = tuple(MARKETS.keys())
# Backward compatibility for existing dashboard integrations.
SYMBOL = "EURUSD"
STARTING_CASH = 10_000.0
TRADE_FRACTION = 0.10
LOOP_SECONDS = 5

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "trader.db"

# Symbols are kept separate in storage and strategy calculations.
# Yahoo Finance is an indicative/delayed public feed for gold and FX;
# Binance public ticker is used for crypto spot pairs.
MARKETS = {
    "XAUUSD": {"name": "Gold (COMEX futures proxy)", "provider": "yahoo", "ticker": "GC=F", "quote": "USD/oz"},
    "EURUSD": {"name": "Euro / US Dollar", "provider": "yahoo", "ticker": "EURUSD=X", "quote": "USD"},
    "GBPUSD": {"name": "British Pound / US Dollar", "provider": "yahoo", "ticker": "GBPUSD=X", "quote": "USD"},
    "USDJPY": {"name": "US Dollar / Japanese Yen", "provider": "yahoo", "ticker": "USDJPY=X", "quote": "JPY"},
    "BTCUSDT": {"name": "Bitcoin / Tether", "provider": "binance", "ticker": "BTC/USDT", "quote": "USDT"},
    "ETHUSDT": {"name": "Ethereum / Tether", "provider": "binance", "ticker": "ETH/USDT", "quote": "USDT"},
}
SYMBOLS = tuple(MARKETS.keys())
# Backward compatibility for existing dashboard integrations.
SYMBOL = "BTC/USDT"
STARTING_CASH = 10_000.0
TRADE_FRACTION = 0.10
LOOP_SECONDS = 5

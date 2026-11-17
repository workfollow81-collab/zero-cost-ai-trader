from pathlib import Path
PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "trader.db"
SYMBOL = "EUR/USD"
STARTING_CASH = 10_000.0
TRADE_FRACTION = 0.10
LOOP_SECONDS = 5

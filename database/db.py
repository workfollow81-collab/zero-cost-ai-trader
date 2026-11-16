import sqlite3
from config import DB_PATH, DATA_DIR

def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS prices (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, price REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, price REAL NOT NULL, quantity REAL NOT NULL, cash_after REAL NOT NULL, note TEXT)")
        con.execute("CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value REAL NOT NULL)")

def save_price(timestamp, symbol, price):
    with connect() as con:
        con.execute("INSERT INTO prices(timestamp, symbol, price) VALUES (?, ?, ?)", (timestamp, symbol, float(price)))

def save_trade(timestamp, symbol, side, price, quantity, cash_after, note=""):
    with connect() as con:
        con.execute("INSERT INTO trades(timestamp, symbol, side, price, quantity, cash_after, note) VALUES (?, ?, ?, ?, ?, ?, ?)", (timestamp, symbol, side, float(price), float(quantity), float(cash_after), note))

def load_rows(table, limit=500):
    if table not in {"prices", "trades"}:
        raise ValueError("Unsupported table")
    with connect() as con:
        rows = con.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(row) for row in rows]


def get_state(key, default):
    with connect() as con:
        row = con.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
        return float(row["value"]) if row else float(default)

def save_state(key, value):
    with connect() as con:
        con.execute(
            "INSERT INTO bot_state(key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, float(value)),
        )

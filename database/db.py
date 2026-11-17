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
        con.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, price REAL NOT NULL, quantity REAL NOT NULL, cash_after REAL NOT NULL, note TEXT, pnl REAL)")
        con.execute("CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, signal TEXT NOT NULL, price REAL NOT NULL, reason TEXT NOT NULL)")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(trades)")}
        if "pnl" not in columns:
            con.execute("ALTER TABLE trades ADD COLUMN pnl REAL")


def save_price(timestamp, symbol, price):
    with connect() as con:
        con.execute("INSERT INTO prices(timestamp, symbol, price) VALUES (?, ?, ?)", (timestamp, symbol, float(price)))


def save_signal(timestamp, symbol, signal, price, reason=""):
    with connect() as con:
        con.execute("INSERT INTO signals(timestamp, symbol, signal, price, reason) VALUES (?, ?, ?, ?, ?)",
                    (timestamp, symbol, signal, float(price), reason))


def save_trade(timestamp, symbol, side, price, quantity, cash_after, note="", pnl=None):
    with connect() as con:
        con.execute("INSERT INTO trades(timestamp, symbol, side, price, quantity, cash_after, note, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, symbol, side, float(price), float(quantity), float(cash_after), note,
                     None if pnl is None else float(pnl)))


def load_rows(table, limit=500, symbol=None):
    if table not in {"prices", "trades", "signals"}:
        raise ValueError("Unsupported table")
    with connect() as con:
        if symbol is None:
            rows = con.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = con.execute(f"SELECT * FROM {table} WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                               (symbol, int(limit))).fetchall()
        return [dict(row) for row in rows]


def get_state(key, default):
    with connect() as con:
        row = con.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
        return float(row["value"]) if row else float(default)


def save_state(key, value):
    with connect() as con:
        con.execute("INSERT INTO bot_state(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, float(value)))

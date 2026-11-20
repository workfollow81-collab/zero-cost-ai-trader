import sqlite3
from contextlib import contextmanager
from config import DB_PATH, DATA_DIR


def connect():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


@contextmanager
def db_connection():
    """Open a connection and always commit/rollback and close it."""
    con = connect()
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def init_db():
    with db_connection() as con:
        con.execute("CREATE TABLE IF NOT EXISTS prices (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, price REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, price REAL NOT NULL, quantity REAL NOT NULL, cash_after REAL NOT NULL, note TEXT, pnl REAL)")
        con.execute("CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, value REAL NOT NULL)")
        con.execute("CREATE TABLE IF NOT EXISTS signals (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL, symbol TEXT NOT NULL, signal TEXT NOT NULL, price REAL NOT NULL, reason TEXT NOT NULL)")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(trades)")}
        if "pnl" not in columns:
            con.execute("ALTER TABLE trades ADD COLUMN pnl REAL")
        con.execute("""CREATE TABLE IF NOT EXISTS strategy_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT, strategy_id TEXT NOT NULL,
            timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL,
            price REAL NOT NULL, quantity REAL NOT NULL, cash_after REAL NOT NULL,
            pnl REAL, note TEXT)""")
        con.execute("""CREATE TABLE IF NOT EXISTS strategy_state (
            strategy_id TEXT NOT NULL, key TEXT NOT NULL, value REAL NOT NULL,
            PRIMARY KEY(strategy_id, key))""")
        con.execute("""CREATE TABLE IF NOT EXISTS strategy_status (
            strategy_id TEXT PRIMARY KEY, signal TEXT NOT NULL,
            reason TEXT NOT NULL, timestamp TEXT NOT NULL)""")
        columns = {row["name"] for row in con.execute("PRAGMA table_info(strategy_trades)")}
        if "notified" not in columns:
            con.execute("ALTER TABLE strategy_trades ADD COLUMN notified INTEGER NOT NULL DEFAULT 1")


def save_price(timestamp, symbol, price):
    with db_connection() as con:
        con.execute("INSERT INTO prices(timestamp, symbol, price) VALUES (?, ?, ?)", (timestamp, symbol, float(price)))


def save_signal(timestamp, symbol, signal, price, reason=""):
    with db_connection() as con:
        con.execute("INSERT INTO signals(timestamp, symbol, signal, price, reason) VALUES (?, ?, ?, ?, ?)",
                    (timestamp, symbol, signal, float(price), reason))


def save_trade(timestamp, symbol, side, price, quantity, cash_after, note="", pnl=None):
    with db_connection() as con:
        con.execute("INSERT INTO trades(timestamp, symbol, side, price, quantity, cash_after, note, pnl) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, symbol, side, float(price), float(quantity), float(cash_after), note,
                     None if pnl is None else float(pnl)))


def load_rows(table, limit=500, symbol=None):
    if table not in {"prices", "trades", "signals"}:
        raise ValueError("Unsupported table")
    with db_connection() as con:
        if symbol is None:
            rows = con.execute(f"SELECT * FROM {table} ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        else:
            rows = con.execute(f"SELECT * FROM {table} WHERE symbol = ? ORDER BY id DESC LIMIT ?",
                               (symbol, int(limit))).fetchall()
        return [dict(row) for row in rows]


def get_state(key, default):
    with db_connection() as con:
        row = con.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
        return float(row["value"]) if row else float(default)


def save_state(key, value):
    with db_connection() as con:
        con.execute("INSERT INTO bot_state(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, float(value)))


def get_strategy_state(strategy_id, key, default=0.0):
    with db_connection() as con:
        row = con.execute("SELECT value FROM strategy_state WHERE strategy_id = ? AND key = ?",
                          (strategy_id, key)).fetchone()
        return float(row["value"]) if row else float(default)


def save_strategy_state(strategy_id, key, value):
    with db_connection() as con:
        con.execute("INSERT INTO strategy_state(strategy_id, key, value) VALUES (?, ?, ?) "
                    "ON CONFLICT(strategy_id, key) DO UPDATE SET value = excluded.value",
                    (strategy_id, key, float(value)))


def save_strategy_trade(strategy_id, timestamp, symbol, side, price, quantity, cash_after, pnl=None, note=""):
    with db_connection() as con:
        cursor = con.execute("""INSERT INTO strategy_trades
            (strategy_id, timestamp, symbol, side, price, quantity, cash_after, pnl, note, notified)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (strategy_id, timestamp, symbol, side, float(price), float(quantity),
             float(cash_after), None if pnl is None else float(pnl), note,
             0 if side == "SELL" else 1))
        return int(cursor.lastrowid)


def load_pending_strategy_notifications():
    with db_connection() as con:
        rows = con.execute("""SELECT s.*,
            (SELECT b.price FROM strategy_trades b WHERE b.strategy_id=s.strategy_id AND b.side='BUY' AND b.id<s.id ORDER BY b.id DESC LIMIT 1) AS entry_price,
            (SELECT b.note FROM strategy_trades b WHERE b.strategy_id=s.strategy_id AND b.side='BUY' AND b.id<s.id ORDER BY b.id DESC LIMIT 1) AS entry_note,
            (SELECT COUNT(*) FROM strategy_trades x WHERE x.strategy_id=s.strategy_id AND x.side='SELL' AND x.pnl IS NOT NULL AND x.id<s.id) AS prior_closed,
            (SELECT COUNT(*) FROM strategy_trades x WHERE x.strategy_id=s.strategy_id AND x.side='SELL' AND x.pnl>0 AND x.id<s.id) AS prior_wins
            FROM strategy_trades s WHERE s.side='SELL' AND s.notified=0 ORDER BY s.id""").fetchall()
        return [dict(row) for row in rows]


def mark_strategy_trade_notified(trade_id):
    with db_connection() as con:
        con.execute("UPDATE strategy_trades SET notified=1 WHERE id=? AND side='SELL'", (int(trade_id),))


def save_strategy_status(strategy_id, signal, reason, timestamp):
    with db_connection() as con:
        con.execute("""INSERT INTO strategy_status(strategy_id, signal, reason, timestamp)
            VALUES (?, ?, ?, ?) ON CONFLICT(strategy_id) DO UPDATE SET
            signal=excluded.signal, reason=excluded.reason, timestamp=excluded.timestamp""",
            (strategy_id, signal, reason, timestamp))

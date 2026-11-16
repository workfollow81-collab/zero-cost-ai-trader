"""Export a safe, read-only snapshot for the public GitHub Pages dashboard."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DB_PATH, STARTING_CASH, SYMBOL

OUTPUT = ROOT / "docs" / "data.json"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prices, trades, signals = [], [], []
    cash, quantity = float(STARTING_CASH), 0.0
    latest_price = None
    realized_pnl = 0.0

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            price_rows = con.execute(
                "SELECT timestamp, price FROM prices ORDER BY id DESC LIMIT 200"
            ).fetchall()
            prices = [{"timestamp": row["timestamp"], "price": float(row["price"])}
                      for row in reversed(price_rows)]
            trade_columns = {row["name"] for row in con.execute("PRAGMA table_info(trades)")}
            pnl_select = "pnl" if "pnl" in trade_columns else "NULL AS pnl"
            trade_rows = con.execute(
                f"SELECT timestamp, side, price, quantity, cash_after, note, {pnl_select} "
                "FROM trades ORDER BY id DESC LIMIT 100"
            ).fetchall()
            trades = [{
                "timestamp": row["timestamp"], "side": row["side"],
                "price": float(row["price"]), "quantity": float(row["quantity"]),
                "cash_after": float(row["cash_after"]), "note": row["note"] or "",
                "pnl": None if row["pnl"] is None else float(row["pnl"]),
            } for row in trade_rows]
            state = {row["key"]: float(row["value"])
                     for row in con.execute("SELECT key, value FROM bot_state")}
            cash = state.get("cash", cash)
            quantity = state.get("quantity", quantity)
            realized_pnl = state.get("realized_pnl", 0.0)
            tables = {row["name"] for row in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "signals" in tables:
                signal_rows = con.execute(
                    "SELECT timestamp, signal, price, reason FROM signals ORDER BY id DESC LIMIT 30"
                ).fetchall()
                signals = [{
                    "timestamp": row["timestamp"], "signal": row["signal"],
                    "price": float(row["price"]), "reason": row["reason"] or "",
                } for row in signal_rows]

    if prices:
        latest_price = prices[-1]["price"]
    equity = cash + quantity * latest_price if latest_price is not None else cash
    closed = [trade for trade in trades if trade["side"] == "SELL" and trade["pnl"] is not None]
    wins = sum(1 for trade in closed if trade["pnl"] > 0)
    win_rate = (wins / len(closed) * 100) if closed else None

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "symbol": SYMBOL, "starting_cash": float(STARTING_CASH),
        "cash": cash, "quantity": quantity, "latest_price": latest_price,
        "equity": equity, "realized_pnl": realized_pnl,
        "closed_trades": len(closed), "winning_trades": wins,
        "losing_trades": sum(1 for trade in closed if trade["pnl"] < 0),
        "win_rate": win_rate, "prices": prices, "trades": trades,
        "signals": signals,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dashboard data exported: {len(prices)} prices, {len(signals)} signals, {len(trades)} paper trades.")


if __name__ == "__main__":
    main()

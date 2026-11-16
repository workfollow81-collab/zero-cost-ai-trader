"""Export a safe, read-only snapshot for the public GitHub Pages dashboard."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DB_PATH, STARTING_CASH, SYMBOL
from dashboard.performance import calculate_performance

OUTPUT = ROOT / "docs" / "data.json"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prices = []
    trades = []
    all_trades = []
    signals = []
    cash = float(STARTING_CASH)
    quantity = 0.0
    latest_price = None

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            price_rows = con.execute(
                "SELECT timestamp, price FROM prices ORDER BY id DESC LIMIT 200"
            ).fetchall()
            prices = [
                {"timestamp": row["timestamp"], "price": float(row["price"])}
                for row in reversed(price_rows)
            ]
            all_trade_rows = con.execute(
                "SELECT id, timestamp, side, price, quantity, cash_after, note "
                "FROM trades ORDER BY id ASC"
            ).fetchall()
            all_trades = [dict(row) for row in all_trade_rows]
            trades = [
                {
                    "timestamp": row["timestamp"],
                    "side": row["side"],
                    "price": float(row["price"]),
                    "quantity": float(row["quantity"]),
                    "cash_after": float(row["cash_after"]),
                    "note": row["note"] or "",
                }
                for row in reversed(all_trades[-50:])
            ]
            signal_rows = con.execute(
                "SELECT timestamp, signal, price, reason "
                "FROM signals ORDER BY id DESC LIMIT 30"
            ).fetchall()
            signals = [
                {
                    "timestamp": row["timestamp"],
                    "signal": row["signal"],
                    "price": float(row["price"]),
                    "reason": row["reason"] or "",
                }
                for row in signal_rows
            ]
            state = {
                row["key"]: float(row["value"])
                for row in con.execute("SELECT key, value FROM bot_state")
            }
            cash = state.get("cash", cash)
            quantity = state.get("quantity", quantity)

    if prices:
        latest_price = prices[-1]["price"]
    equity = cash + quantity * latest_price if latest_price is not None else cash
    performance = calculate_performance(
        all_trades, cash, quantity, latest_price, STARTING_CASH
    )

    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "symbol": SYMBOL,
        "starting_cash": float(STARTING_CASH),
        "cash": cash,
        "quantity": quantity,
        "latest_price": latest_price,
        "equity": equity,
        "performance": performance,
        "prices": prices,
        "trades": trades,
        "signals": signals,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Dashboard data exported: {len(prices)} prices, {len(trades)} recent trades, "
        f"{len(signals)} recent signals."
    )


if __name__ == "__main__":
    main()

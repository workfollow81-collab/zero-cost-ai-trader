"""Export a safe, read-only snapshot for the public GitHub Pages dashboard."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import DB_PATH, STARTING_CASH, SYMBOL
from strategies.portfolio import STRATEGIES

OUTPUT = ROOT / "docs" / "data.json"
STATE_PREFIX = SYMBOL.replace("/", "")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    prices, trades, signals = [], [], []
    cash, quantity = float(STARTING_CASH), 0.0
    latest_price = None
    realized_pnl = 0.0
    strategy_rows = []

    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            price_rows = con.execute(
                "SELECT timestamp, price FROM prices WHERE symbol = ? ORDER BY id DESC LIMIT 200",
                (SYMBOL,),
            ).fetchall()
            prices = [{"timestamp": row["timestamp"], "price": float(row["price"])}
                      for row in reversed(price_rows)]
            trade_columns = {row["name"] for row in con.execute("PRAGMA table_info(trades)")}
            pnl_select = "pnl" if "pnl" in trade_columns else "NULL AS pnl"
            trade_rows = con.execute(
                f"SELECT timestamp, side, price, quantity, cash_after, note, {pnl_select} "
                "FROM trades WHERE symbol = ? ORDER BY id DESC LIMIT 100",
                (SYMBOL,),
            ).fetchall()
            trades = [{
                "timestamp": row["timestamp"], "side": row["side"],
                "price": float(row["price"]), "quantity": float(row["quantity"]),
                "cash_after": float(row["cash_after"]), "note": row["note"] or "",
                "pnl": None if row["pnl"] is None else float(row["pnl"]),
            } for row in trade_rows]
            state = {row["key"]: float(row["value"])
                     for row in con.execute("SELECT key, value FROM bot_state")}
            cash = state.get(f"{STATE_PREFIX}_cash", cash)
            quantity = state.get(f"{STATE_PREFIX}_quantity", quantity)
            realized_pnl = state.get(f"{STATE_PREFIX}_realized_pnl", 0.0)
            signal_rows = con.execute(
                "SELECT timestamp, signal, price, reason FROM signals WHERE symbol = ? ORDER BY id DESC LIMIT 30",
                (SYMBOL,),
            ).fetchall()
            signals = [{
                "timestamp": row["timestamp"], "signal": row["signal"],
                "price": float(row["price"]), "reason": row["reason"] or "",
            } for row in signal_rows]

            strategy_state = {}
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='strategy_state'").fetchone():
                strategy_state = {(row["strategy_id"], row["key"]): float(row["value"])
                                  for row in con.execute("SELECT strategy_id, key, value FROM strategy_state")}
            strategy_status = {}
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='strategy_status'").fetchone():
                strategy_status = {row["strategy_id"]: dict(row)
                                   for row in con.execute("SELECT * FROM strategy_status")}
            strategy_trades = []
            if con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='strategy_trades'").fetchone():
                strategy_trades = [dict(row) for row in con.execute(
                    "SELECT strategy_id, timestamp, symbol, side, price, quantity, cash_after, pnl, note "
                    "FROM strategy_trades ORDER BY id DESC LIMIT 300")]

            for definition in STRATEGIES:
                sid = definition["id"]
                closed = [t for t in strategy_trades if t["strategy_id"] == sid
                          and t["side"] == "SELL" and t["pnl"] is not None]
                wins = sum(1 for t in closed if float(t["pnl"]) > 0)
                losses = sum(1 for t in closed if float(t["pnl"]) < 0)
                strat_cash = strategy_state.get((sid, "cash"), float(STARTING_CASH))
                strat_qty = strategy_state.get((sid, "quantity"), 0.0)
                strat_pnl = sum(float(t["pnl"]) for t in closed)
                status = strategy_status.get(sid, {})
                recent = [t for t in strategy_trades if t["strategy_id"] == sid][:10]
                strategy_rows.append({
                    **definition,
                    "signal": status.get("signal", "HOLD"),
                    "reason": status.get("reason", "بانتظار أول دورة تحليل"),
                    "last_update": status.get("timestamp"),
                    "cash": strat_cash,
                    "quantity": strat_qty,
                    "equity": strat_cash + strat_qty * (latest_price or 0),
                    "realized_pnl": strat_pnl,
                    "closed_trades": len(closed),
                    "wins": wins,
                    "losses": losses,
                    "win_rate": wins / len(closed) * 100 if closed else None,
                    "trades": [{
                        "timestamp": t["timestamp"], "side": t["side"],
                        "price": float(t["price"]), "quantity": float(t["quantity"]),
                        "pnl": None if t["pnl"] is None else float(t["pnl"]),
                        "note": t["note"] or "",
                    } for t in recent],
                })

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
        "signals": signals, "strategies": strategy_rows,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Dashboard data exported for {SYMBOL}: {len(prices)} prices, "
          f"{len(signals)} signals, {len(trades)} base paper trades, "
          f"{len(strategy_rows)} strategy portfolios.")


if __name__ == "__main__":
    main()

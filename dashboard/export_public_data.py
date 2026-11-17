"""Export a read-only multi-market snapshot for the public dashboard."""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import DB_PATH, STARTING_CASH, SYMBOLS, MARKETS

OUTPUT = ROOT / "docs" / "data.json"


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    markets = {}
    total_cash = STARTING_CASH
    total_equity = STARTING_CASH
    total_realized = 0.0
    all_trades = []
    if DB_PATH.exists():
        with sqlite3.connect(DB_PATH) as con:
            con.row_factory = sqlite3.Row
            state = {r["key"]: float(r["value"]) for r in con.execute("SELECT key, value FROM bot_state")}
            total_cash = state.get("cash", STARTING_CASH)
            total_equity = total_cash
            for symbol in SYMBOLS:
                prices = con.execute(
                    "SELECT timestamp, price FROM prices WHERE symbol=? ORDER BY id DESC LIMIT 200",
                    (symbol,),
                ).fetchall()
                prices = [{"timestamp": r["timestamp"], "price": float(r["price"])} for r in reversed(prices)]
                rows = con.execute(
                    "SELECT timestamp, side, price, quantity, cash_after, note, pnl FROM trades WHERE symbol=? ORDER BY id DESC LIMIT 100",
                    (symbol,),
                ).fetchall()
                trades = [{
                    "timestamp": r["timestamp"], "symbol": symbol, "side": r["side"],
                    "price": float(r["price"]), "quantity": float(r["quantity"]),
                    "cash_after": float(r["cash_after"]), "note": r["note"] or "",
                    "pnl": None if r["pnl"] is None else float(r["pnl"]),
                } for r in rows]
                all_trades.extend(trades)
                signals = con.execute(
                    "SELECT timestamp, signal, price, reason FROM signals WHERE symbol=? ORDER BY id DESC LIMIT 30",
                    (symbol,),
                ).fetchall()
                quantity = state.get(f"quantity:{symbol}", 0.0)
                latest = prices[-1]["price"] if prices else None
                total_equity += quantity * (latest or 0.0)
                closed = [t for t in trades if t["side"] == "SELL" and t["pnl"] is not None]
                wins = sum(1 for t in closed if t["pnl"] > 0)
                total_realized += state.get(f"realized_pnl:{symbol}", 0.0)
                markets[symbol] = {
                    "name": MARKETS[symbol]["name"], "provider": MARKETS[symbol]["provider"],
                    "quote": MARKETS[symbol]["quote"], "latest_price": latest,
                    "quantity": quantity, "prices": prices, "trades": trades,
                    "signals": [{"timestamp": r["timestamp"], "signal": r["signal"],
                                 "price": float(r["price"]), "reason": r["reason"]} for r in signals],
                    "closed_trades": len(closed), "wins": wins,
                    "win_rate": (wins / len(closed) * 100) if closed else None,
                    "realized_pnl": state.get(f"realized_pnl:{symbol}", 0.0),
                }
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "starting_cash": STARTING_CASH, "cash": total_cash, "equity": total_equity,
        "realized_pnl": total_realized, "markets": markets,
        "trades": sorted(all_trades, key=lambda t: t["timestamp"], reverse=True)[:100],
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported multi-market dashboard for {len(markets)} symbols.")


if __name__ == "__main__":
    main()

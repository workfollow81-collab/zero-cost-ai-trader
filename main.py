import argparse
import time
from datetime import datetime

import pandas as pd

from config import SYMBOLS, MARKETS, STARTING_CASH, TRADE_FRACTION, LOOP_SECONDS
from database.db import (
    init_db, save_price, save_signal, save_trade, load_rows, get_state, save_state,
)
from analysis.indicators import add_indicators
from strategies.basic import get_signal
from exchange.market_data import fetch_current_price


def run_cycle():
    """Fetch all configured markets and paper-trade them using one shared cash balance."""
    init_db()
    cash = get_state("cash", STARTING_CASH)
    # Migrate the previous single-BTC paper position without discarding it.
    if get_state("migration_multi_asset_v1", 0.0) == 0.0:
        legacy_qty = get_state("quantity", 0.0)
        if legacy_qty > 0:
            save_state("quantity:BTCUSDT", legacy_qty)
            save_state("position_cost:BTCUSDT", get_state("position_cost", 0.0))
        save_state("quantity", 0.0)
        save_state("migration_multi_asset_v1", 1.0)

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    latest_prices = {}
    for symbol in SYMBOLS:
        try:
            price = fetch_current_price(symbol)
            latest_prices[symbol] = price
            save_price(now, symbol, price)
            rows = list(reversed(load_rows("prices", 300, symbol=symbol)))
            frame = pd.DataFrame(rows)
            signal, reason = ("HOLD", "نجمع بيانات كافية أولاً")
            if len(frame) >= 25:
                frame = add_indicators(frame)
                signal, reason = get_signal(frame)
            save_signal(now, symbol, signal, price, reason)

            qty_key = f"quantity:{symbol}"
            cost_key = f"position_cost:{symbol}"
            quantity = get_state(qty_key, 0.0)
            if signal == "BUY" and quantity <= 0 and cash > 0:
                budget = cash * TRADE_FRACTION
                bought = budget / price
                cash -= budget
                quantity += bought
                save_state(qty_key, quantity)
                save_state(cost_key, budget)
                save_trade(now, symbol, "BUY", price, bought, cash, reason)
                print(f"{symbol}: PAPER BUY {bought:.8f} @ {price:.6f}")
            elif signal == "SELL" and quantity > 0:
                proceeds = quantity * price
                cost_basis = get_state(cost_key, 0.0)
                pnl = proceeds - cost_basis
                cash += proceeds
                save_state(qty_key, 0.0)
                save_state(cost_key, 0.0)
                save_state(f"realized_pnl:{symbol}", get_state(f"realized_pnl:{symbol}", 0.0) + pnl)
                save_trade(now, symbol, "SELL", price, quantity, cash, reason, pnl=pnl)
                print(f"{symbol}: PAPER SELL {quantity:.8f} @ {price:.6f} | PnL {pnl:.2f}")
            print(f"{symbol} ({MARKETS[symbol]['name']}): {price:.6f} | {signal} | {reason}")
        except Exception as exc:
            # One unavailable provider must not prevent other markets from running.
            print(f"{symbol}: SKIPPED — {exc}")

    for symbol, price in latest_prices.items():
        # Current position state is already persisted per market.
        pass
    equity = cash
    for symbol in SYMBOLS:
        qty = get_state(f"quantity:{symbol}", 0.0)
        mark = latest_prices.get(symbol)
        if mark is None:
            rows = load_rows("prices", 1, symbol=symbol)
            mark = rows[0]["price"] if rows else 0.0
        equity += qty * mark
    save_state("cash", cash)
    save_state("equity", equity)
    print(f"{now} | CASH={cash:.2f} | PORTFOLIO EQUITY={equity:.2f} | PAPER ONLY")


def main():
    parser = argparse.ArgumentParser(description="Multi-asset paper trading simulator")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    args = parser.parse_args()
    print("ZERO COST AI TRADER | MULTI-ASSET PAPER MODE")
    print("Markets: " + ", ".join(SYMBOLS))
    print("No broker connection, no real orders, no real funds.")
    if args.once:
        run_cycle()
        return
    print("Continuous local mode; press Ctrl+C to stop.")
    try:
        while True:
            run_cycle()
            time.sleep(LOOP_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped safely. All results are simulated.")


if __name__ == "__main__":
    main()

import argparse
import time
from datetime import datetime

import pandas as pd

from config import SYMBOL, STARTING_CASH, TRADE_FRACTION, LOOP_SECONDS
import database.db as db
from database.db import (
    init_db, save_price, save_signal, save_trade, load_rows, get_state, save_state,
)
from analysis.indicators import add_indicators
from strategies.basic import get_signal
from exchange.paper_broker import PaperBroker
from exchange.market_data import fetch_current_price
from strategies.portfolio import run_strategy_portfolios

# Keep each market's virtual portfolio separate from any older BTC/USDT state.
STATE_PREFIX = SYMBOL.replace("/", "")


def run_cycle():
    """Run one EUR/USD market-analysis cycle with virtual orders only."""
    init_db()
    broker = PaperBroker(
        STARTING_CASH,
        cash=get_state(f"{STATE_PREFIX}_cash", STARTING_CASH),
        quantity=get_state(f"{STATE_PREFIX}_quantity", 0.0),
    )

    price = fetch_current_price(SYMBOL)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    save_price(now, SYMBOL, price)

    rows = list(reversed(load_rows("prices", 300, SYMBOL)))
    frame = pd.DataFrame(rows)
    signal, reason = ("HOLD", "نجمع بيانات كافية أولاً")
    if len(frame) >= 25:
        frame = add_indicators(frame)
        signal, reason = get_signal(frame)

    save_signal(now, SYMBOL, signal, price, reason)

    if signal == "BUY" and broker.quantity == 0:
        previous_cash = broker.cash
        qty = broker.buy(price, TRADE_FRACTION)
        if qty:
            invested = previous_cash - broker.cash
            save_state(f"{STATE_PREFIX}_position_cost", invested)
            save_trade(now, SYMBOL, "BUY", price, qty, broker.cash, reason)
            print(f"شراء افتراضي: {qty:.6f} EUR بسعر {price:.5f} USD")
    elif signal == "SELL" and broker.quantity > 0:
        qty = broker.sell_all(price)
        cost_basis = get_state(f"{STATE_PREFIX}_position_cost", 0.0)
        realized_pnl = qty * price - cost_basis
        cumulative_pnl = get_state(f"{STATE_PREFIX}_realized_pnl", 0.0) + realized_pnl
        save_state(f"{STATE_PREFIX}_realized_pnl", cumulative_pnl)
        save_state(f"{STATE_PREFIX}_position_cost", 0.0)
        save_trade(now, SYMBOL, "SELL", price, qty, broker.cash, reason, pnl=realized_pnl)
        print(f"بيع افتراضي: {qty:.6f} EUR بسعر {price:.5f} USD | الربح/الخسارة: {realized_pnl:.2f} USD")

    save_state(f"{STATE_PREFIX}_cash", broker.cash)
    save_state(f"{STATE_PREFIX}_quantity", broker.quantity)

    # Run six isolated strategy portfolios; these never touch the MT5 bridge.
    run_strategy_portfolios(frame, price, now, SYMBOL, db, STARTING_CASH, TRADE_FRACTION)

    equity = broker.cash + broker.quantity * price
    print(
        f"{now} | {SYMBOL}={price:.5f} USD لكل EUR | {signal} | "
        f"النقد={broker.cash:,.2f} USD | الكمية={broker.quantity:.6f} EUR | "
        f"قيمة المحفظة={equity:,.2f} USD | {reason}"
    )


def main():
    parser = argparse.ArgumentParser(description="EUR/USD paper trading simulator")
    parser.add_argument("--once", action="store_true",
                        help="نفّذ دورة واحدة ثم اخرج (مخصص لـ GitHub Actions)")
    args = parser.parse_args()

    print("ZERO COST AI TRADER | EUR/USD | PAPER MODE")
    print("سعر صرف عام + صفقات افتراضية فقط — لا اتصال بحساب تداول ولا تداول حقيقي")
    if args.once:
        run_cycle()
        return

    print("وضع التشغيل المحلي المستمر؛ للإيقاف اضغط Ctrl + C")
    try:
        while True:
            run_cycle()
            time.sleep(LOOP_SECONDS)
    except KeyboardInterrupt:
        print("\nتم إيقاف البوت بأمان. النتائج افتراضية فقط.")


if __name__ == "__main__":
    main()

import argparse
import time
from datetime import datetime

import pandas as pd

from config import SYMBOL, STARTING_CASH, TRADE_FRACTION, LOOP_SECONDS
from database.db import (
    init_db, save_price, save_signal, save_trade, load_rows, get_state, save_state,
)
from analysis.indicators import add_indicators
from strategies.basic import get_signal
from exchange.paper_broker import PaperBroker
from exchange.market_data import fetch_current_price


def run_cycle():
    """نفّذ دورة واحدة باستخدام سعر السوق العام وصفقات افتراضية فقط."""
    init_db()
    broker = PaperBroker(
        STARTING_CASH,
        cash=get_state("cash", STARTING_CASH),
        quantity=get_state("quantity", 0.0),
    )

    # لا نستخدم سعراً عشوائياً عند تعذر الاتصال؛ نتوقف بأمان دون صفقة.
    price = fetch_current_price(SYMBOL)
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    save_price(now, SYMBOL, price)

    rows = list(reversed(load_rows("prices", 300)))
    frame = pd.DataFrame(rows)
    signal, reason = ("HOLD", "انتظار البيانات")
    if len(frame) >= 25:
        frame = add_indicators(frame)
        signal, reason = get_signal(frame)

    # احفظ كل إشارة، بما فيها HOLD، لأغراض قياس الأداء.
    save_signal(now, SYMBOL, signal, price, reason)

    if signal == "BUY" and broker.quantity == 0:
        previous_cash = broker.cash
        qty = broker.buy(price, TRADE_FRACTION)
        if qty:
            invested = previous_cash - broker.cash
            save_state("position_cost", invested)
            save_trade(now, SYMBOL, "BUY", price, qty, broker.cash, reason)
            print(f"شراء افتراضي: {qty:.6f} بسعر {price:.2f}")
    elif signal == "SELL" and broker.quantity > 0:
        qty = broker.sell_all(price)
        cost_basis = get_state("position_cost", 0.0)
        realized_pnl = qty * price - cost_basis
        cumulative_pnl = get_state("realized_pnl", 0.0) + realized_pnl
        save_state("realized_pnl", cumulative_pnl)
        save_state("position_cost", 0.0)
        save_trade(now, SYMBOL, "SELL", price, qty, broker.cash, reason, pnl=realized_pnl)
        print(f"بيع افتراضي: {qty:.6f} بسعر {price:.2f} | ربح/خسارة محققة: {realized_pnl:.2f} USDT")

    # حفظ حالة المحفظة بين مرات تشغيل GitHub Actions.
    save_state("cash", broker.cash)
    save_state("quantity", broker.quantity)

    equity = broker.cash + broker.quantity * price
    print(
        f"{now} | {SYMBOL}={price:,.2f} (سعر سوق عام) | {signal} | "
        f"النقد={broker.cash:,.2f} | الكمية={broker.quantity:.8f} | "
        f"قيمة المحفظة={equity:,.2f} | {reason}"
    )


def main():
    parser = argparse.ArgumentParser(description="Paper trading simulator")
    parser.add_argument(
        "--once", action="store_true",
        help="نفّذ دورة واحدة ثم اخرج (مخصص لـ GitHub Actions)",
    )
    args = parser.parse_args()

    print("ZERO COST AI TRADER | PAPER MODE")
    print("سعر سوق عام + صفقات افتراضية فقط — لا اتصال بحساب تداول ولا تداول حقيقي")
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

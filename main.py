import argparse
import time
from datetime import datetime

import pandas as pd

from config import SYMBOL, STARTING_CASH, TRADE_FRACTION, LOOP_SECONDS
from database.db import (
    init_db, save_price, save_trade, load_rows, get_state, save_state,
)
from analysis.indicators import add_indicators
from strategies.basic import get_signal
from exchange.paper_broker import PaperBroker
from core.market_simulator import MarketSimulator


def run_cycle():
    """نفّذ دورة واحدة؛ مناسبة للتشغيل المجدول على GitHub Actions."""
    init_db()
    market = MarketSimulator(start_price=get_state("last_price", 60000.0))
    broker = PaperBroker(
        STARTING_CASH,
        cash=get_state("cash", STARTING_CASH),
        quantity=get_state("quantity", 0.0),
    )

    price = market.next_price()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    save_price(now, SYMBOL, price)

    rows = list(reversed(load_rows("prices", 300)))
    frame = pd.DataFrame(rows)
    signal, reason = ("HOLD", "انتظار البيانات")
    if len(frame) >= 25:
        frame = add_indicators(frame)
        signal, reason = get_signal(frame)

    if signal == "BUY" and broker.quantity == 0:
        qty = broker.buy(price, TRADE_FRACTION)
        if qty:
            save_trade(now, SYMBOL, "BUY", price, qty, broker.cash, reason)
            print(f"شراء افتراضي: {qty:.6f} بسعر {price:.2f}")
    elif signal == "SELL" and broker.quantity > 0:
        qty = broker.sell_all(price)
        save_trade(now, SYMBOL, "SELL", price, qty, broker.cash, reason)
        print(f"بيع افتراضي: {qty:.6f} بسعر {price:.2f}")

    # حفظ حالة المحفظة والسعر حتى تستمر المحاكاة بين مرات تشغيل GitHub Actions.
    save_state("last_price", market.price)
    save_state("cash", broker.cash)
    save_state("quantity", broker.quantity)

    equity = broker.cash + broker.quantity * price
    print(
        f"{now} | {SYMBOL}={price:,.2f} | {signal} | "
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
    print("محاكاة أسعار وصفقات افتراضية فقط — لا اتصال بمنصة ولا تداول حقيقي")
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

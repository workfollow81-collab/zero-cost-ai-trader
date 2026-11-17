"""Demo-only MetaTrader 5 execution bridge.

This module refuses to trade unless explicitly enabled and the connected account
is confirmed by MetaTrader as a demo account on the exact configured demo server.
"""
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd

from analysis.indicators import add_indicators
from strategies.basic import get_signal

MAGIC = 261117
STATE_FILE = Path("data/mt5_demo_state.json")
DEFAULT_SYMBOL = "EURUSD"
DEFAULT_VOLUME = 0.01
MAX_DAILY_LOSS_PCT = 2.0
DEFAULT_MAX_SPREAD_POINTS = 30


def required_environment():
    if os.getenv("MT5_DEMO_TRADING_ENABLED", "").strip().lower() != "true":
        print("MT5 demo execution is disabled; no broker orders will be sent.")
        return None

    login = os.getenv("MT5_LOGIN", "").strip()
    password = os.getenv("MT5_PASSWORD", "")
    server = os.getenv("MT5_SERVER", "").strip()
    if not login or not password or not server:
        raise RuntimeError(
            "MT5 demo mode is enabled, but MT5_LOGIN, MT5_PASSWORD, or MT5_SERVER is missing."
        )
    if not login.isdigit():
        raise RuntimeError("MT5_LOGIN must contain the numeric demo account number.")
    if "demo" not in server.lower():
        raise RuntimeError("Safety stop: MT5_SERVER must identify a demo server.")
    return int(login), password, server


def load_last_bar():
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8")).get("last_action_bar")
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def save_last_bar(bar_time):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"last_action_bar": int(bar_time)}, indent=2),
        encoding="utf-8",
    )


def choose_filling(info):
    mode = int(getattr(info, "filling_mode", 0))
    if mode & int(getattr(mt5, "SYMBOL_FILLING_IOC", 2)):
        return mt5.ORDER_FILLING_IOC
    if mode & int(getattr(mt5, "SYMBOL_FILLING_FOK", 1)):
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


def normalized_volume(info):
    requested = float(os.getenv("MT5_VOLUME", "").strip() or DEFAULT_VOLUME)
    if not math.isfinite(requested) or requested <= 0:
        raise RuntimeError("MT5_VOLUME must be a positive number.")

    minimum = float(info.volume_min)
    maximum = float(info.volume_max)
    step = float(info.volume_step)
    if step <= 0 or requested < minimum:
        raise RuntimeError(
            f"Configured volume {requested} is below the symbol minimum {minimum}."
        )
    volume = math.floor((min(requested, maximum) + 1e-12) / step) * step
    if volume < minimum:
        raise RuntimeError("Could not calculate a valid order volume.")
    decimals = max(0, min(8, len(str(step).split(".")[-1].rstrip("0"))))
    return round(volume, decimals)


def daily_realized_pnl():
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(start, now)
    if deals is None:
        raise RuntimeError(f"Could not read today's MT5 deal history: {mt5.last_error()}")
    return sum(
        float(deal.profit) + float(deal.swap) + float(deal.commission)
        for deal in deals
        if int(getattr(deal, "magic", 0)) == MAGIC
    )


def check_and_send(request):
    check = mt5.order_check(request)
    if check is None:
        raise RuntimeError(f"MT5 order_check failed: {mt5.last_error()}")
    if int(check.retcode) not in (0, int(mt5.TRADE_RETCODE_DONE)):
        raise RuntimeError(
            f"MT5 rejected the order check (retcode={check.retcode}): {check.comment}"
        )

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"MT5 order_send failed: {mt5.last_error()}")
    accepted = {
        int(mt5.TRADE_RETCODE_DONE),
        int(mt5.TRADE_RETCODE_PLACED),
        int(getattr(mt5, "TRADE_RETCODE_DONE_PARTIAL", 10010)),
    }
    if int(result.retcode) not in accepted:
        raise RuntimeError(
            f"MT5 did not execute the order (retcode={result.retcode}): {result.comment}"
        )
    print(
        f"MT5 demo order accepted: {result.comment}; "
        f"order={getattr(result, 'order', 0)}; deal={getattr(result, 'deal', 0)}"
    )
    return result


def run():
    credentials = required_environment()
    if credentials is None:
        return 0

    login, password, server = credentials
    terminal_path = os.getenv("MT5_TERMINAL_PATH", "").strip()
    init_args = {"login": login, "password": password, "server": server, "timeout": 60000}
    if terminal_path:
        init_args["path"] = terminal_path

    try:
        if not mt5.initialize(**init_args):
            raise RuntimeError(f"Could not initialize MetaTrader 5: {mt5.last_error()}")

        account = mt5.account_info()
        terminal = mt5.terminal_info()
        if account is None or terminal is None:
            raise RuntimeError(f"Could not read MT5 account/terminal information: {mt5.last_error()}")

        # Hard safety interlock: account mode must be demo and server must exactly match the configured demo server.
        if int(account.trade_mode) != int(mt5.ACCOUNT_TRADE_MODE_DEMO):
            raise RuntimeError("Safety stop: connected MT5 account is not a demo account.")
        if str(account.server).strip().casefold() != server.strip().casefold():
            raise RuntimeError("Safety stop: connected MT5 server does not exactly match MT5_SERVER.")
        if int(account.login) != login:
            raise RuntimeError("Safety stop: connected MT5 account number does not match MT5_LOGIN.")
        if not bool(terminal.trade_allowed) or not bool(account.trade_allowed):
            raise RuntimeError("MT5 terminal/account trading permission is disabled.")

        symbol = os.getenv("MT5_SYMBOL", "").strip() or DEFAULT_SYMBOL
        if not symbol or not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"Could not select MT5 symbol '{symbol}': {mt5.last_error()}")

        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if info is None or tick is None or float(info.point) <= 0:
            raise RuntimeError(f"Could not read symbol details or quote for {symbol}.")

        spread_points = (float(tick.ask) - float(tick.bid)) / float(info.point)
        max_spread = float(os.getenv("MT5_MAX_SPREAD_POINTS", "").strip() or DEFAULT_MAX_SPREAD_POINTS)
        if int(info.trade_mode) == int(mt5.SYMBOL_TRADE_MODE_DISABLED):
            raise RuntimeError(f"Trading is disabled for symbol {symbol}.")

        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, 150)
        if rates is None or len(rates) < 30:
            raise RuntimeError(f"Insufficient closed M5 candles for {symbol}: {mt5.last_error()}")

        frame = pd.DataFrame(rates)
        frame["price"] = frame["close"].astype(float)
        frame = add_indicators(frame)
        signal, reason = get_signal(frame)
        bar_time = int(frame.iloc[-1]["time"])
        candle_time = datetime.fromtimestamp(bar_time).astimezone().isoformat(timespec="seconds")
        print(
            f"MT5 demo | {symbol} | closed M5 candle {candle_time} | "
            f"signal={signal} | spread={spread_points:.1f} points | {reason}"
        )

        positions = mt5.positions_get(symbol=symbol)
        if positions is None:
            raise RuntimeError(f"Could not read open positions: {mt5.last_error()}")
        foreign_positions = [p for p in positions if int(p.magic) != MAGIC]
        if foreign_positions:
            raise RuntimeError(
                "Safety stop: this symbol has a position not opened by this bot; "
                "manual positions will never be modified."
            )
        bot_positions = [p for p in positions if int(p.magic) == MAGIC]

        if signal == "BUY" and not bot_positions:
            last_action_bar = load_last_bar()
            if last_action_bar == bar_time:
                print("Duplicate-bar guard: this candle was already processed; no new order.")
                return 0
            if spread_points > max_spread:
                print(f"Spread guard: {spread_points:.1f} points exceeds {max_spread:.1f}; no new position.")
                return 0

            pnl_today = daily_realized_pnl()
            daily_limit = float(account.balance) * MAX_DAILY_LOSS_PCT / 100.0
            if pnl_today <= -daily_limit:
                print(
                    f"Daily loss guard: realized P/L {pnl_today:.2f} reached "
                    f"the -{MAX_DAILY_LOSS_PCT:.1f}% limit; no new position."
                )
                return 0

            volume = normalized_volume(info)
            previous_close = frame["close"].shift(1)
            true_range = pd.concat(
                [
                    frame["high"] - frame["low"],
                    (frame["high"] - previous_close).abs(),
                    (frame["low"] - previous_close).abs(),
                ],
                axis=1,
            ).max(axis=1)
            atr = float(true_range.rolling(14).mean().iloc[-1])
            if not math.isfinite(atr) or atr <= 0:
                raise RuntimeError("ATR is unavailable; refusing to place an order.")

            minimum_stop = max(float(info.trade_stops_level) * float(info.point), 2 * float(info.point))
            stop_distance = max(1.5 * atr, minimum_stop)
            take_distance = max(3.0 * atr, minimum_stop)
            price = float(tick.ask)
            digits = int(info.digits)
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_BUY,
                "price": price,
                "sl": round(price - stop_distance, digits),
                "tp": round(price + take_distance, digits),
                "deviation": 20,
                "magic": MAGIC,
                "comment": "ZERO_COST_AI_TRADER demo",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": choose_filling(info),
            }
            check_and_send(request)
            save_last_bar(bar_time)

        elif signal == "SELL" and bot_positions:
            for position in bot_positions:
                close_tick = mt5.symbol_info_tick(symbol)
                if close_tick is None:
                    raise RuntimeError(f"Could not refresh quote before closing: {mt5.last_error()}")
                close_type = (
                    mt5.ORDER_TYPE_SELL
                    if int(position.type) == int(mt5.POSITION_TYPE_BUY)
                    else mt5.ORDER_TYPE_BUY
                )
                close_price = float(close_tick.bid if close_type == mt5.ORDER_TYPE_SELL else close_tick.ask)
                request = {
                    "action": mt5.TRADE_ACTION_DEAL,
                    "symbol": symbol,
                    "position": int(position.ticket),
                    "volume": float(position.volume),
                    "type": close_type,
                    "price": close_price,
                    "deviation": 20,
                    "magic": MAGIC,
                    "comment": "ZERO_COST_AI_TRADER demo close",
                    "type_time": mt5.ORDER_TIME_GTC,
                    "type_filling": choose_filling(info),
                }
                check_and_send(request)
            save_last_bar(bar_time)
        else:
            print("No eligible demo order for this signal and current bot position.")

        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    try:
        sys.exit(run())
    except Exception as exc:
        print(f"MT5 DEMO ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

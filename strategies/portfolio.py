"""Independent, price-only paper portfolios for dashboard strategy comparison."""
import math
import pandas as pd

STRATEGIES = [
    {"id": "ema_rsi", "name": "EMA + RSI", "description": "تقاطع EMA 9/21 مع فلتر RSI"},
    {"id": "macd", "name": "MACD", "description": "تقاطع MACD مع خط الإشارة"},
    {"id": "rsi_reversion", "name": "RSI Reversion", "description": "ارتداد RSI من مناطق التشبع"},
    {"id": "bollinger", "name": "Bollinger Reversion", "description": "الارتداد من نطاق بولينجر"},
    {"id": "donchian", "name": "Donchian Breakout", "description": "اختراق أعلى/أدنى نطاق سعري سابق"},
    {"id": "ema_momentum", "name": "EMA Momentum", "description": "اتجاه EMA 12/26 مع تأكيد السعر"},
]

ATR_PERIOD = 14
STOP_ATR_MULTIPLIER = 1.5
TAKE_PROFIT_ATR_MULTIPLIER = 3.0


def _price_atr(frame):
    """ATR proxy for this price-only feed: 14-period mean absolute price change."""
    changes = frame["price"].astype(float).diff().abs()
    value = changes.rolling(ATR_PERIOD, min_periods=ATR_PERIOD).mean().iloc[-1]
    return float(value) if pd.notna(value) and math.isfinite(float(value)) else None


def _features(frame):
    out = frame.copy()
    close = out["price"].astype(float)
    out["ema9"] = close.ewm(span=9, adjust=False).mean()
    out["ema12"] = close.ewm(span=12, adjust=False).mean()
    out["ema21"] = close.ewm(span=21, adjust=False).mean()
    out["ema26"] = close.ewm(span=26, adjust=False).mean()
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    out["rsi"] = 100 - 100 / (1 + rs)
    out.loc[(loss == 0) & (gain > 0), "rsi"] = 100.0
    out.loc[(loss == 0) & (gain == 0), "rsi"] = 50.0
    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    out["macd"] = macd
    out["macd_signal"] = macd.ewm(span=9, adjust=False).mean()
    mid = close.rolling(20, min_periods=20).mean()
    std = close.rolling(20, min_periods=20).std(ddof=0)
    out["bb_mid"] = mid
    out["bb_upper"] = mid + 2 * std
    out["bb_lower"] = mid - 2 * std
    out["donchian_high"] = close.shift(1).rolling(20, min_periods=20).max()
    out["donchian_low"] = close.shift(1).rolling(20, min_periods=20).min()
    return out


def generate_signals(frame, in_positions=None):
    """Return one independent BUY/SELL/HOLD decision per strategy."""
    in_positions = in_positions or {}
    if len(frame) < 30:
        return {s["id"]: ("HOLD", "بيانات غير كافية؛ نحتاج 30 قراءة سعرية على الأقل")
                for s in STRATEGIES}
    data = _features(frame)
    p, c = data.iloc[-2], data.iloc[-1]
    signals = {}

    def set_signal(key, buy, sell, buy_reason, sell_reason):
        active = bool(in_positions.get(key, False))
        if not active and buy:
            signals[key] = ("BUY", buy_reason)
        elif active and sell:
            signals[key] = ("SELL", sell_reason)
        else:
            signals[key] = ("HOLD", "لا توجد إشارة دخول أو خروج مكتملة")

    set_signal("ema_rsi",
        p.ema9 <= p.ema21 and c.ema9 > c.ema21 and c.rsi < 70,
        p.ema9 >= p.ema21 and c.ema9 < c.ema21,
        "تقاطع EMA 9 أعلى EMA 21 و RSI دون 70",
        "تقاطع EMA 9 أسفل EMA 21")
    set_signal("macd",
        p.macd <= p.macd_signal and c.macd > c.macd_signal,
        p.macd >= p.macd_signal and c.macd < c.macd_signal,
        "تقاطع MACD صعوداً فوق خط الإشارة",
        "تقاطع MACD هبوطاً أسفل خط الإشارة")
    set_signal("rsi_reversion",
        p.rsi >= 30 and c.rsi < 30,
        c.rsi >= 55,
        "RSI دخل منطقة التشبع البيعي دون 30",
        "RSI ارتد إلى 55 أو أعلى")
    set_signal("bollinger",
        p.price >= p.bb_lower and c.price < c.bb_lower,
        c.price >= c.bb_mid,
        "السعر كسر الحد السفلي لبولينجر",
        "السعر عاد إلى متوسط بولينجر")
    set_signal("donchian",
        c.price > c.donchian_high,
        c.price < c.donchian_low,
        "اختراق أعلى سعر في آخر 20 قراءة مكتملة",
        "كسر أدنى سعر في آخر 20 قراءة مكتملة")
    set_signal("ema_momentum",
        c.ema12 > c.ema26 and c.price > c.ema12 and p.ema12 <= p.ema26,
        c.ema12 < c.ema26 and c.price < c.ema12,
        "تقاطع زخم EMA 12/26 مع تأكيد السعر",
        "تحول الزخم إلى هابط")
    return signals


def run_strategy_portfolios(frame, price, timestamp, symbol, db, starting_cash, trade_fraction):
    """Advance isolated paper portfolios with independent ATR-based SL/TP."""
    atr = _price_atr(frame) if len(frame) >= 30 else None
    statuses = generate_signals(frame, {
        item["id"]: db.get_strategy_state(item["id"], "quantity", 0.0) > 0
        for item in STRATEGIES
    })
    for item in STRATEGIES:
        sid = item["id"]
        signal, reason = statuses[sid]
        cash = db.get_strategy_state(sid, "cash", starting_cash)
        quantity = db.get_strategy_state(sid, "quantity", 0.0)
        cost = db.get_strategy_state(sid, "position_cost", 0.0)
        stop_loss = db.get_strategy_state(sid, "stop_loss", 0.0)
        take_profit = db.get_strategy_state(sid, "take_profit", 0.0)

        # Protect legacy open positions that predate persisted SL/TP levels.
        if quantity > 0 and (stop_loss <= 0 or take_profit <= 0) and atr and atr > 0:
            entry = cost / quantity if quantity else price
            stop_loss = entry - STOP_ATR_MULTIPLIER * atr
            take_profit = entry + TAKE_PROFIT_ATR_MULTIPLIER * atr
            db.save_strategy_state(sid, "stop_loss", stop_loss)
            db.save_strategy_state(sid, "take_profit", take_profit)

        exit_reason = None
        if quantity > 0 and stop_loss > 0 and price <= stop_loss:
            exit_reason = "إغلاق بوقف الخسارة ATR (1.5×)"
        elif quantity > 0 and take_profit > 0 and price >= take_profit:
            exit_reason = "إغلاق بجني الأرباح ATR (3×)"
        elif signal == "SELL" and quantity > 0:
            exit_reason = reason

        if signal == "BUY" and quantity <= 0 and cash > 0 and price > 0:
            if not atr or atr <= 0:
                reason = "تم تجاهل الدخول لعدم توفر ATR صالح لحساب وقف الخسارة"
            else:
                budget = cash * trade_fraction
                qty = budget / price
                stop_loss = price - STOP_ATR_MULTIPLIER * atr
                take_profit = price + TAKE_PROFIT_ATR_MULTIPLIER * atr
                cash -= budget
                quantity = qty
                cost = budget
                db.save_strategy_trade(sid, timestamp, symbol, "BUY", price, qty, cash, None,
                                       f"{reason} | SL={stop_loss:.5f} | TP={take_profit:.5f}")
                db.save_strategy_state(sid, "stop_loss", stop_loss)
                db.save_strategy_state(sid, "take_profit", take_profit)
        elif exit_reason and quantity > 0 and price > 0:
            qty = quantity
            pnl = qty * price - cost
            cash += qty * price
            db.save_strategy_trade(sid, timestamp, symbol, "SELL", price, qty, cash, pnl, exit_reason)
            quantity = 0.0
            cost = 0.0
            stop_loss = 0.0
            take_profit = 0.0
            signal = "SELL"
            reason = exit_reason

        db.save_strategy_state(sid, "cash", cash)
        db.save_strategy_state(sid, "quantity", quantity)
        db.save_strategy_state(sid, "position_cost", cost)
        db.save_strategy_state(sid, "stop_loss", stop_loss)
        db.save_strategy_state(sid, "take_profit", take_profit)
        db.save_strategy_status(sid, signal, reason, timestamp)

def get_signal(frame):
    if len(frame) < 25:
        return "HOLD", "نجمع بيانات كافية أولاً"
    previous, current = frame.iloc[-2], frame.iloc[-1]
    if previous["ema_fast"] <= previous["ema_slow"] and current["ema_fast"] > current["ema_slow"] and current["rsi"] < 70:
        return "BUY", "تقاطع صاعد للمتوسطات"
    if previous["ema_fast"] >= previous["ema_slow"] and current["ema_fast"] < current["ema_slow"]:
        return "SELL", "تقاطع هابط للمتوسطات"
    return "HOLD", "لا توجد إشارة واضحة"

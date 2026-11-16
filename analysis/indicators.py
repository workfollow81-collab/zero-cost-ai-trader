import pandas as pd


def add_indicators(frame):
    out = frame.copy()
    out["ema_fast"] = out["price"].ewm(span=9, adjust=False).mean()
    out["ema_slow"] = out["price"].ewm(span=21, adjust=False).mean()

    delta = out["price"].diff()
    gain = delta.clip(lower=0).rolling(14, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).rolling(14, min_periods=14).mean()

    # عالج الحالات الحدّية حتى لا يصبح RSI غير معرّف:
    # ارتفاع متواصل = 100، ثبات كامل = 50، وهبوط متواصل = 0.
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((loss == 0) & (gain > 0), 100.0)
    rsi = rsi.mask((loss == 0) & (gain == 0), 50.0)
    out["rsi"] = rsi

    return out

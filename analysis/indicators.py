import pandas as pd

def add_indicators(frame):
    out = frame.copy()
    out["ema_fast"] = out["price"].ewm(span=9, adjust=False).mean()
    out["ema_slow"] = out["price"].ewm(span=21, adjust=False).mean()
    delta = out["price"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    out["rsi"] = 100 - (100 / (1 + rs))
    return out

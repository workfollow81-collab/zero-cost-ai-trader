"""Fetch public market prices for paper trading only."""
import json
import math
from urllib.error import URLError
from urllib.request import Request, urlopen


def _read_json(url):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0 zero-cost-paper-trading-bot/1.0"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_current_price(symbol):
    """Return a live public quote; never invent a fallback price."""
    if symbol.upper() == "EUR/USD":
        # Yahoo Finance FX ticker: EURUSD=X (USD for one EUR).
        payload = _read_json(
            "https://query1.finance.yahoo.com/v8/finance/chart/EURUSD=X?range=1d&interval=1m"
        )
        chart = payload.get("chart", {})
        if chart.get("error") or not chart.get("result"):
            raise RuntimeError(f"تعذر جلب سعر {symbol}: {chart.get('error')}")
        price = float(chart["result"][0]["meta"]["regularMarketPrice"])
    else:
        market_symbol = symbol.replace("/", "").replace("-", "").upper()
        if not market_symbol.isalnum():
            raise ValueError(f"رمز تداول غير صالح: {symbol}")
        try:
            payload = _read_json(
                f"https://data-api.binance.vision/api/v3/ticker/price?symbol={market_symbol}"
            )
            price = float(payload["price"])
        except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            raise RuntimeError(f"تعذر جلب سعر {symbol} من واجهة السوق العامة: {exc}") from exc

    if not math.isfinite(price) or price <= 0:
        raise RuntimeError(f"أعادت واجهة السوق سعراً غير صالح للزوج {symbol}")
    return price

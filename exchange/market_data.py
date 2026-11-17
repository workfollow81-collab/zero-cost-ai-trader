"""Public market data adapters. No exchange account or API key is used."""
import json
import math
from urllib.error import URLError
from urllib.request import Request, urlopen

from config import MARKETS


def _get_json(url):
    request = Request(url, headers={"User-Agent": "zero-cost-paper-trading-bot/1.0"})
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_current_price(symbol):
    """Return a validated quote; never fabricate a fallback price."""
    if symbol not in MARKETS:
        raise ValueError(f"Unsupported market symbol: {symbol}")
    market = MARKETS[symbol]
    try:
        if market["provider"] == "binance":
            pair = market["ticker"].replace("/", "").upper()
            payload = _get_json(
                f"https://data-api.binance.vision/api/v3/ticker/price?symbol={pair}"
            )
            price = float(payload["price"])
        else:
            # Yahoo's public chart endpoint is unofficial; FX/commodity quotes
            # may be delayed or indicative and availability is not guaranteed.
            ticker = market["ticker"]
            from urllib.parse import quote
            payload = _get_json(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(ticker, safe='')}?range=1d&interval=5m"
            )
            result = payload["chart"]["result"][0]
            price = float(result["meta"]["regularMarketPrice"])
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        raise RuntimeError(f"Unable to fetch a valid {symbol} quote: {exc}") from exc

    if not math.isfinite(price) or price <= 0:
        raise RuntimeError(f"Invalid market quote for {symbol}: {price}")
    return price

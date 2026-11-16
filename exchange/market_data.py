"""جلب سعر السوق الحالي من واجهة Binance العامة دون مفتاح API."""

import json
import math
from urllib.error import URLError
from urllib.request import Request, urlopen


def fetch_current_price(symbol):
    """أعد آخر سعر معلن للزوج، أو ارفع خطأ واضحاً دون اختلاق سعر بديل."""
    market_symbol = symbol.replace("/", "").replace("-", "").upper()
    if not market_symbol.isalnum():
        raise ValueError(f"رمز تداول غير صالح: {symbol}")

    url = f"https://api.binance.com/api/v3/ticker/price?symbol={market_symbol}"
    request = Request(
        url,
        headers={"User-Agent": "zero-cost-paper-trading-bot/1.0"},
    )

    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        price = float(payload["price"])
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(
            f"تعذر جلب سعر {symbol} من واجهة السوق العامة: {exc}"
        ) from exc

    if not math.isfinite(price) or price <= 0:
        raise RuntimeError(f"أعادت واجهة السوق سعراً غير صالح للزوج {symbol}")

    return price

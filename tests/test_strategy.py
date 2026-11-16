import unittest

import pandas as pd

from analysis.indicators import add_indicators
from strategies.basic import get_signal


def signal_frame(fast_previous, fast_current, rsi_previous, rsi_current):
    return pd.DataFrame({
        "ema_fast": [fast_previous] * 24 + [fast_current],
        "ema_slow": [100.0] * 25,
        "rsi": [rsi_previous] * 24 + [rsi_current],
    })


class IndicatorTests(unittest.TestCase):
    def test_rsi_is_100_for_continuous_rise(self):
        frame = pd.DataFrame({"price": list(range(100, 120))})

        result = add_indicators(frame)

        self.assertEqual(result["rsi"].iloc[-1], 100.0)

    def test_rsi_is_50_for_flat_prices(self):
        frame = pd.DataFrame({"price": [100.0] * 20})

        result = add_indicators(frame)

        self.assertEqual(result["rsi"].iloc[-1], 50.0)

    def test_rsi_is_zero_for_continuous_fall(self):
        frame = pd.DataFrame({"price": list(range(120, 100, -1))})

        result = add_indicators(frame)

        self.assertEqual(result["rsi"].iloc[-1], 0.0)

    def test_buy_signal_on_valid_bullish_cross(self):
        frame = signal_frame(99.0, 101.0, 55.0, 60.0)

        self.assertEqual(get_signal(frame)[0], "BUY")

    def test_overbought_cross_does_not_buy(self):
        frame = signal_frame(99.0, 101.0, 65.0, 75.0)

        self.assertEqual(get_signal(frame)[0], "HOLD")

    def test_sell_signal_on_bearish_cross(self):
        frame = signal_frame(101.0, 99.0, 60.0, 45.0)

        self.assertEqual(get_signal(frame)[0], "SELL")


if __name__ == "__main__":
    unittest.main()

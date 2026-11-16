import unittest

import pandas as pd

from analysis.indicators import add_indicators
from strategies.basic import get_signal


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
        frame = pd.DataFrame({
            "ema_fast": [99.0, 101.0],
            "ema_slow": [100.0, 100.0],
            "rsi": [55.0, 60.0],
        })

        self.assertEqual(get_signal(frame)[0], "BUY")

    def test_overbought_cross_does_not_buy(self):
        frame = pd.DataFrame({
            "ema_fast": [99.0, 101.0],
            "ema_slow": [100.0, 100.0],
            "rsi": [65.0, 75.0],
        })

        self.assertEqual(get_signal(frame)[0], "HOLD")

    def test_sell_signal_on_bearish_cross(self):
        frame = pd.DataFrame({
            "ema_fast": [101.0, 99.0],
            "ema_slow": [100.0, 100.0],
            "rsi": [60.0, 45.0],
        })

        self.assertEqual(get_signal(frame)[0], "SELL")


if __name__ == "__main__":
    unittest.main()

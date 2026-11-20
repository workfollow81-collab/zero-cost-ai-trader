import unittest
import pandas as pd

from strategies.portfolio import (
    ATR_PERIOD, STOP_ATR_MULTIPLIER, TAKE_PROFIT_ATR_MULTIPLIER,
    STRATEGIES, _price_atr, generate_signals,
)


class StrategyPortfolioTests(unittest.TestCase):
    def test_all_strategies_return_independent_decisions(self):
        frame = pd.DataFrame({"price": [1.10 + i * 0.0001 for i in range(80)]})
        result = generate_signals(frame)
        self.assertEqual(set(result), {item["id"] for item in STRATEGIES})
        self.assertTrue(all(value[0] in {"BUY", "SELL", "HOLD"} for value in result.values()))

    def test_insufficient_history_holds_all_strategies(self):
        frame = pd.DataFrame({"price": [1.1, 1.2]})
        result = generate_signals(frame)
        self.assertTrue(all(signal == "HOLD" for signal, _ in result.values()))

    def test_strategy_positions_are_respected(self):
        frame = pd.DataFrame({"price": [1.10 + i * 0.0001 for i in range(80)]})
        result = generate_signals(frame, {"ema_rsi": True})
        self.assertIn(result["ema_rsi"][0], {"SELL", "HOLD"})

    def test_price_only_atr_proxy_and_risk_reward_multipliers(self):
        frame = pd.DataFrame({"price": [1.0 + i * 0.001 for i in range(40)]})
        self.assertAlmostEqual(_price_atr(frame), 0.001)
        self.assertEqual(ATR_PERIOD, 14)
        self.assertEqual(STOP_ATR_MULTIPLIER, 1.5)
        self.assertEqual(TAKE_PROFIT_ATR_MULTIPLIER, 3.0)

    def test_atr_proxy_requires_enough_price_changes(self):
        frame = pd.DataFrame({"price": [1.0, 1.1, 1.2]})
        self.assertIsNone(_price_atr(frame))


if __name__ == "__main__":
    unittest.main()

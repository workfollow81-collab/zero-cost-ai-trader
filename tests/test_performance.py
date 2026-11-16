import unittest

from dashboard.performance import calculate_performance


class PerformanceTests(unittest.TestCase):
    def test_closed_winning_trade(self):
        trades = [
            {"id": 1, "side": "BUY", "price": 100.0, "quantity": 2.0},
            {"id": 2, "side": "SELL", "price": 110.0, "quantity": 2.0},
        ]
        result = calculate_performance(trades, 1020.0, 0.0, 110.0, 1000.0)
        self.assertAlmostEqual(result["realized_pnl"], 20.0)
        self.assertEqual(result["closed_trades"], 1)
        self.assertEqual(result["winning_trades"], 1)
        self.assertEqual(result["win_rate"], 100.0)

    def test_open_position_has_unrealized_profit(self):
        trades = [{"id": 1, "side": "BUY", "price": 100.0, "quantity": 2.0}]
        result = calculate_performance(trades, 800.0, 2.0, 105.0, 1000.0)
        self.assertAlmostEqual(result["unrealized_pnl"], 10.0)
        self.assertEqual(result["closed_trades"], 0)

    def test_losing_trade(self):
        trades = [
            {"id": 1, "side": "BUY", "price": 100.0, "quantity": 1.0},
            {"id": 2, "side": "SELL", "price": 90.0, "quantity": 1.0},
        ]
        result = calculate_performance(trades, 990.0, 0.0, 90.0, 1000.0)
        self.assertAlmostEqual(result["realized_pnl"], -10.0)
        self.assertEqual(result["losing_trades"], 1)
        self.assertEqual(result["win_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()

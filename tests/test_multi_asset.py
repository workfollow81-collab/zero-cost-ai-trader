import tempfile
import unittest
from pathlib import Path

import pandas as pd

import database.db as db
from config import MARKETS, SYMBOLS
from analysis.indicators import add_indicators
from exchange.paper_broker import PaperBroker


class MultiAssetTests(unittest.TestCase):
    def test_expected_markets_are_configured(self):
        self.assertIn("XAUUSD", SYMBOLS)
        self.assertIn("EURUSD", SYMBOLS)
        self.assertIn("GBPUSD", SYMBOLS)
        self.assertNotIn("BTCUSDT", SYMBOLS)
        self.assertNotIn("ETHUSDT", SYMBOLS)
        self.assertEqual(set(SYMBOLS), set(MARKETS))

    def test_market_price_histories_are_isolated_by_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            original_path, original_dir = db.DB_PATH, db.DATA_DIR
            try:
                db.DB_PATH = Path(tmp) / "test.sqlite"
                db.DATA_DIR = Path(tmp)
                db.init_db()
                db.save_price("2026-01-01T00:00:00+00:00", "EURUSD", 1.1)
                db.save_price("2026-01-01T00:00:00+00:00", "XAUUSD", 2000.0)
                self.assertEqual(len(db.load_rows("prices", 10, symbol="EURUSD")), 1)
                self.assertEqual(db.load_rows("prices", 10, symbol="EURUSD")[0]["price"], 1.1)
                self.assertEqual(db.load_rows("prices", 10, symbol="XAUUSD")[0]["price"], 2000.0)
            finally:
                db.DB_PATH, db.DATA_DIR = original_path, original_dir

    def test_paper_broker_uses_virtual_cash_only(self):
        broker = PaperBroker(1000.0)
        qty = broker.buy(100.0, 0.10)
        self.assertAlmostEqual(qty, 1.0)
        self.assertAlmostEqual(broker.cash, 900.0)
        sold = broker.sell_all(110.0)
        self.assertAlmostEqual(sold, 1.0)
        self.assertAlmostEqual(broker.cash, 1010.0)
        self.assertAlmostEqual(broker.quantity, 0.0)

    def test_indicator_edge_cases_remain_finite(self):
        for values, expected in [
            ([float(i) for i in range(1, 31)], 100.0),
            ([5.0] * 30, 50.0),
            ([float(30 - i) for i in range(30)], 0.0),
        ]:
            result = add_indicators(pd.DataFrame({"price": values}))
            self.assertAlmostEqual(float(result["rsi"].iloc[-1]), expected)


if __name__ == "__main__":
    unittest.main()

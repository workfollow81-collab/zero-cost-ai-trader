import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import db


class PerformanceTrackingTests(unittest.TestCase):
    def test_existing_database_is_upgraded_and_records_are_saved(self):
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "trader.db"
            data_dir = Path(tmp) / "data"
            data_dir.mkdir()
            # Simulate a database created by the earlier bot version.
            legacy_con = sqlite3.connect(db_path)
            try:
                legacy_con.execute(
                    "CREATE TABLE trades (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "timestamp TEXT NOT NULL, symbol TEXT NOT NULL, side TEXT NOT NULL, "
                    "price REAL NOT NULL, quantity REAL NOT NULL, cash_after REAL NOT NULL, note TEXT)"
                )
                legacy_con.commit()
            finally:
                legacy_con.close()

            with patch.object(db, "DB_PATH", db_path), patch.object(db, "DATA_DIR", data_dir):
                db.init_db()
                with db.db_connection() as con:
                    columns = {row["name"] for row in con.execute("PRAGMA table_info(trades)")}
                self.assertIn("pnl", columns)

                db.save_signal("2026-11-16T20:00:00+00:00", "BTC/USDT", "HOLD", 65000, "no signal")
                db.save_trade("2026-11-16T20:05:00+00:00", "BTC/USDT", "SELL",
                              66000, 0.01, 10010, "test close", pnl=10)

                signals = db.load_rows("signals")
                trades = db.load_rows("trades")
                self.assertEqual(signals[0]["signal"], "HOLD")
                self.assertAlmostEqual(trades[0]["pnl"], 10.0)


if __name__ == "__main__":
    unittest.main()

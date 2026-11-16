import io
import unittest
from unittest.mock import patch
from urllib.error import URLError

from exchange.market_data import fetch_current_price


class MarketDataTests(unittest.TestCase):
    @patch("exchange.market_data.urlopen")
    def test_fetches_and_parses_public_price(self, mock_urlopen):
        mock_urlopen.return_value = io.BytesIO(
            b'{"symbol":"BTCUSDT","price":"65000.12"}'
        )

        price = fetch_current_price("BTC/USDT")

        self.assertEqual(price, 65000.12)
        request = mock_urlopen.call_args.args[0]
        self.assertIn("symbol=BTCUSDT", request.full_url)

    def test_rejects_invalid_symbol(self):
        with self.assertRaises(ValueError):
            fetch_current_price("BTC/USDT?")

    @patch("exchange.market_data.urlopen")
    def test_rejects_missing_price(self, mock_urlopen):
        mock_urlopen.return_value = io.BytesIO(b'{"symbol":"BTCUSDT"}')

        with self.assertRaises(RuntimeError):
            fetch_current_price("BTC/USDT")

    @patch("exchange.market_data.urlopen")
    def test_rejects_zero_price(self, mock_urlopen):
        mock_urlopen.return_value = io.BytesIO(b'{"price":"0"}')

        with self.assertRaises(RuntimeError):
            fetch_current_price("BTC/USDT")

    @patch("exchange.market_data.urlopen", side_effect=URLError("offline"))
    def test_fails_safely_when_endpoint_is_unavailable(self, mock_urlopen):
        with self.assertRaises(RuntimeError):
            fetch_current_price("BTC/USDT")


if __name__ == "__main__":
    unittest.main()

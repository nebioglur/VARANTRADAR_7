import unittest
from datetime import datetime, timezone

from data.cache_freshness import cache_is_stale, mark_prices_updated


class CacheFreshnessTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
        self.today = self.now.strftime("%Y-%m-%d")

    def test_recent_real_price_update_is_fresh(self):
        cache = {"cache_date": self.today, "price_updated_at": self.now.timestamp() - 5 * 60}
        self.assertFalse(cache_is_stale(cache, self.now)[0])

    def test_old_price_update_is_stale_even_if_other_cache_writes_are_recent(self):
        cache = {
            "cache_date": self.today,
            "price_updated_at": self.now.timestamp() - 60 * 60,
            "cache_timestamp": self.now.timestamp(),
        }
        self.assertTrue(cache_is_stale(cache, self.now)[0])

    def test_missing_price_timestamp_is_stale(self):
        self.assertTrue(cache_is_stale({"cache_date": self.today}, self.now)[0])

    def test_previous_day_snapshot_is_stale(self):
        cache = {"cache_date": "2026-11-05", "price_updated_at": self.now.timestamp()}
        self.assertTrue(cache_is_stale(cache, self.now)[0])

    def test_successful_fetch_stamps_cache_date_and_price_time(self):
        cache = mark_prices_updated({}, self.now)
        self.assertEqual(cache["cache_date"], self.today)
        self.assertEqual(cache["price_updated_at"], self.now.timestamp())
        self.assertFalse(cache_is_stale(cache, self.now)[0])


if __name__ == "__main__":
    unittest.main()

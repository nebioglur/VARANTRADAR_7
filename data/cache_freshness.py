"""Market cache freshness rules shared by the dashboard and background worker."""
from datetime import datetime
from zoneinfo import ZoneInfo


CACHE_MAX_AGE_MINUTES = 30


def cache_is_stale(data, now=None):
    """Return stale status using a market-data timestamp, not generic cache writes."""
    now = now or datetime.now(ZoneInfo("Europe/Istanbul"))
    if not isinstance(data, dict) or not data:
        return True, "cache bos"

    today_str = now.strftime("%Y-%m-%d")
    cache_date = data.get("cache_date")
    if cache_date != today_str:
        return True, f"onceki gunun cache'i ({cache_date})"

    # Older snapshots have no price_updated_at. Their cache_timestamp is
    # accepted temporarily for backward compatibility.
    timestamp = data.get("price_updated_at") or data.get("cache_timestamp")
    if not timestamp:
        return True, "fiyat guncelleme zamani bilinmiyor"
    try:
        age_min = (now.timestamp() - float(timestamp)) / 60
    except (TypeError, ValueError, OverflowError):
        return True, "fiyat guncelleme zamani gecersiz"
    if age_min > CACHE_MAX_AGE_MINUTES:
        return True, f"cache {int(age_min)} dk eski"
    return False, f"cache {max(0, int(age_min))} dk oncesi"


def mark_prices_updated(data, now=None):
    """Stamp a cache only after a successful real market-data fetch."""
    now = now or datetime.now(ZoneInfo("Europe/Istanbul"))
    data["price_updated_at"] = now.timestamp()
    data["cache_date"] = now.strftime("%Y-%m-%d")
    return data

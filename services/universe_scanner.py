"""
YENİ HİSSE TARAYICI.
Yahoo screener (yfinance >= 1.7) ile tum BIST ozkaynaklarini tarar,
son N gunde borsaya giren (ilk islem tarihi yeni) hisseleri bulur.
Sonuc 6 saat cache'lenir; radar motoru yeni hisseleri analize dahil eder.
"""
import threading
import time
from datetime import datetime

_cache = {
    "new_listings": [],   # [{symbol, listed, age_days, price, change_pct}]
    "total_universe": 0,
    "built_at": None,
    "building": False,
    "error": None,
}
# Yahoo screener Render IP'sinde sik sik yanit vermez; bir kez alinan iyi
# listeyi hic zaman kaybetmemek icin ayrica sakliyoruz.
_last_good = {
    "new_listings": [],
    "built_at": None,
}
_lock = threading.Lock()
_build_lock = threading.Lock()

TTL = 6 * 3600  # 6 saat


def _db_save(listings, built_at):
    """Son iyi listeyi DB'ye kaydet (restart'a dayaniklilik). Best-effort."""
    try:
        import json as _json
        from services.trade_database import get_connection
        payload = _json.dumps({"built_at": str(built_at), "listings": listings})
        conn = get_connection()
        c = conn.cursor()
        c.execute("INSERT INTO live_settings (key, value) VALUES ('new_listings_cache', %s) "
                  "ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value", (payload,))
        conn.commit()
        conn.close()
    except Exception:
        pass


def _db_load():
    """DB'deki son iyi listeyi dondurur; yoksa []."""
    try:
        import json as _json
        from services.trade_database import get_connection
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM live_settings WHERE key='new_listings_cache'")
        row = c.fetchone()
        conn.close()
        if not row:
            return []
        # sqlite/Pg farki: satir dict veya tuple gelebilir
        val = row["value"] if isinstance(row, dict) else row[0]
        data = _json.loads(val)
        return data.get("listings") or []
    except Exception:
        return []


def get_new_listings(max_age_days=180, sync_if_empty=True):
    """(new_listings, built_at, error) dondurur; bayat ise yeniler.

    sync_if_empty: hic insa edilmemisse ilk insayi senkron yapar (60-90 sn
    surebilir ama radar ilk insada yeni hisseleri kacirmaz). Sonraki
    cagrilarda cache kullanilir.
    Screener hata verirse sirayla: bellek -> DB'deki son iyi liste.
    """
    with _lock:
        never_built = _cache["built_at"] is None and not _cache["building"]
    if sync_if_empty and never_built:
        _build(max_age_days)
    else:
        _maybe_build(max_age_days)
    with _lock:
        if _cache["new_listings"]:
            return _cache["new_listings"], _cache["built_at"], _cache["error"]
        if _last_good["new_listings"]:
            return _last_good["new_listings"], _last_good["built_at"], _cache["error"]
    # bellek bos: DB'ye bak (restart sonrasi)
    saved = _db_load()
    if saved:
        return saved, None, _cache["error"]
    with _lock:
        return _cache["new_listings"], _cache["built_at"], _cache["error"]


def get_universe_size():
    with _lock:
        return _cache["total_universe"]


def _maybe_build(max_age_days=180):
    with _lock:
        built_at = _cache["built_at"]
        building = _cache["building"]
    stale = built_at is None or (datetime.now() - built_at).total_seconds() > TTL
    if (stale or _cache["error"]) and not building:
        t = threading.Thread(target=_build, args=(max_age_days,), daemon=True)
        t.start()


def _scan_quotes():
    """Tum TR hisselerini screener uzerinden sayfa sayfa ceker."""
    from yfinance.screener import screener as scr_mod
    from yfinance.screener.query import EquityQuery

    q = EquityQuery('eq', ['region', 'tr'])
    quotes = []
    for off in (0, 250, 500):
        try:
            r = scr_mod.screen(q, size=250, offset=off,
                               sortField='intradaymarketcap', sortAsc=False)
        except Exception:
            continue
        page = r.get('quotes', [])
        quotes.extend(page)
        if len(page) < 250:
            break
    # ayni sembol tekrarlari
    seen = set()
    uniq = []
    for x in quotes:
        s = x.get('symbol')
        if s and s.endswith('.IS') and s not in seen:
            seen.add(s)
            uniq.append(x)
    return uniq


def _build(max_age_days=180):
    with _build_lock:
        with _lock:
            if _cache["building"]:
                return
            _cache["building"] = True
        try:
            # screener tek denemede sik patliyor; 3 deneme hakki
            quotes = []
            for attempt in range(3):
                quotes = _scan_quotes()
                if quotes:
                    break
                time.sleep(4 * (attempt + 1))
            if not quotes:
                # ONCEKI IYI VERIYI KORU - bos listeyle ezme
                with _lock:
                    _cache["error"] = "Screener yanıt vermedi (son iyi liste korunuyor)"
                return
            now = time.time()
            fresh = []
            for x in quotes:
                ftd = x.get('firstTradeDateMilliseconds')
                if not ftd:
                    continue
                age = (now - ftd / 1000) / 86400
                if age <= max_age_days:
                    fresh.append({
                        "symbol": x['symbol'],
                        "listed": datetime.fromtimestamp(ftd / 1000).strftime('%Y-%m-%d'),
                        "age_days": int(age),
                        "price": float(x['regularMarketPrice']) if x.get('regularMarketPrice') else None,
                        "change_pct": float(x['regularMarketChangePercent'] * 100) if x.get('regularMarketChangePercent') is not None else None,
                    })
            fresh.sort(key=lambda v: v["age_days"])  # en yeni once
            with _lock:
                _cache["new_listings"] = fresh
                _cache["total_universe"] = len(quotes)
                _cache["built_at"] = datetime.now()
                _cache["error"] = None
                if fresh:
                    _last_good["new_listings"] = list(fresh)
                    _last_good["built_at"] = _cache["built_at"]
            if fresh:
                _db_save(fresh, _cache["built_at"])
        except Exception as e:
            with _lock:
                _cache["error"] = str(e)
        finally:
            with _lock:
                _cache["building"] = False

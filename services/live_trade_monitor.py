"""
Canlı İşlem Terminali Motoru:
- Manuel anlık alım/satım (open/close)
- Arka planda calisan AKILLI KAR AL / ZARAR KES izleyicisi:
  * Sabit TP (Kâr Al) ve SL (Zarar Kes) seviyeleri
  * +3% kazanctan sonra otomatik IZLEYEN STOP (trailing) devreye girer
  * Tavan hedefine ulasinda tam kâr
  * Seans sonu (18:10) otomatik pozisyon kapatma
Komisyon: %0.04 (islem basi, cift yonlu) - sim motoru ile ayni.
"""
import time
import threading
from datetime import datetime, time as dtime

from services.trade_database import get_connection

COMMISSION = 0.0004
TRAIL_ACTIVATION = 3.0   # +3% kazancta izleyen stop devreye girer
DEFAULT_TRAIL_PCT = 1.5  # zirveden %1.5 geri cekilmede kilitle

LIVE_BUDGET_CAP = 100000.0  # guvenlik ust limiti


def _get_setting(key, default=None):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM live_settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


def _set_setting(key, value):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO live_settings (key, value) VALUES (?, ?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    conn.commit()
    conn.close()


def _get_live_price(symbol):
    """Guncel fiyat: once dashboard cache, sonra yfinance."""
    clean = symbol.replace(".IS", "").replace(".is", "").upper().strip()
    try:
        from server import GLOBAL_DASHBOARD_CACHE
        stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {}) if isinstance(GLOBAL_DASHBOARD_CACHE, dict) else {}
        info = stats.get(clean) or stats.get(clean + ".IS")
        if isinstance(info, dict):
            p = info.get("Price") or info.get("Daily_Close")
            if p:
                return float(p), "cache"
    except Exception:
        pass
    try:
        import yfinance as yf
        hist = yf.Ticker(clean + ".IS").history(period="1d", interval="5m")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1]), "yfinance"
    except Exception:
        pass
    try:
        import yfinance as yf
        hist = yf.Ticker(clean + ".IS").history(period="5d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1]), "yfinance_daily"
    except Exception:
        pass
    return None, "none"


def _bulk_prices(symbols):
    """Coklu sembol icin toplu fiyat cekimi (1d/5m once, sonra 5d/1d fallback)."""
    import yfinance as yf
    import pandas as pd
    result = {}
    if not symbols:
        return result
    clean = [s.replace(".IS", "").upper() for s in symbols]
    tickers = [s + ".IS" for s in clean]
    for period, interval in [("1d", "5m"), ("5d", "1d")]:
        try:
            data = yf.download(tickers, period=period, interval=interval, group_by="ticker",
                               progress=False, threads=True)
            if data is None or data.empty:
                continue
            for sym in tickers:
                if sym in result:
                    continue
                try:
                    if len(tickers) == 1:
                        df = data.dropna(how="all")
                    else:
                        df = data[sym].dropna(how="all")
                    if df is not None and not df.empty:
                        result[sym.replace(".IS", "")] = float(df["Close"].iloc[-1])
                except Exception:
                    continue
        except Exception:
            continue
        if len(result) == len(tickers):
            break
    return result


def open_position(symbol, allocation=2000.0, tp_pct=5.0, sl_pct=3.0, trailing=True, source="MANUAL"):
    """Yeni pozisyon acar. (success, message) dondurur."""
    clean = symbol.replace(".IS", "").replace(".is", "").upper().strip()
    if not clean:
        return False, "Sembol gerekli"

    try:
        allocation = float(allocation)
    except (TypeError, ValueError):
        return False, "Gecersiz tutar"
    if allocation < 100:
        return False, "Minimum islem tutari 100 TL"

    try:
        tp_pct = float(tp_pct) if tp_pct is not None else 5.0
        sl_pct = abs(float(sl_pct)) if sl_pct is not None else 3.0
    except (TypeError, ValueError):
        tp_pct, sl_pct = 5.0, 3.0

    price, src = _get_live_price(clean)
    if not price or price <= 0:
        return False, f"{clean} icin guncel fiyat alinamadi"

    cash = float(_get_setting("live_cash", "10000.0") or 0)
    if allocation > cash:
        return False, f"Yetersiz bakiye (Kullanilabilir: {cash:.2f} TL)"

    entry_price = round(price * 1.0015, 2)  # slipaj
    shares = int(allocation // entry_price)
    if shares <= 0:
        return False, "Bu fiyattan lot alinamadi (tutar cok dusuk)"

    cost = shares * entry_price * (1 + COMMISSION)
    if cost > cash:
        shares = int(cash // (entry_price * (1 + COMMISSION)))
        if shares <= 0:
            return False, "Yetersiz bakiye"
        cost = shares * entry_price * (1 + COMMISSION)

    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    d_str = now[:10]
    c.execute("""INSERT INTO live_positions
                 (date_str, symbol, entry_time, entry_price, shares, cost_val,
                  stop_price, tp_price, trail_pct, high_water, trailing_active,
                  status, source, last_price, last_update)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)""",
              (d_str, clean, now, entry_price, shares, cost,
               round(entry_price * (1 - sl_pct / 100.0), 2),
               round(entry_price * (1 + tp_pct / 100.0), 2),
               DEFAULT_TRAIL_PCT if trailing else 0,
               entry_price, source, price, now))
    c.execute("UPDATE live_settings SET value=? WHERE key='live_cash'", (str(round(cash - cost, 2)),))
    conn.commit()
    conn.close()
    return True, (f"ALINDI: {shares} lot {clean} @ {entry_price:.2f} TL "
                  f"(TP %{tp_pct:.1f} / SL -%{sl_pct:.1f})")


def close_position(pos_id, price=None, reason="MANUEL KAPATMA"):
    """Pozisyonu kapatir, PnL gerceklestirir."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE id=? AND status='OPEN'", (pos_id,))
    row = c.fetchone()
    if row is None:
        conn.close()
        return False, "Pozisyon bulunamadi (zaten kapali olabilir)"

    symbol = row["symbol"]
    conn.close()

    if price is None:
        price, _ = _get_live_price(symbol)
    if not price or price <= 0:
        return False, f"{symbol} icin guncel fiyat alinamadi"

    entry = float(row["entry_price"])
    shares = int(row["shares"])
    cost = float(row["cost_val"] or (shares * entry * (1 + COMMISSION)))

    sell_volume = shares * price
    commission = (shares * entry + sell_volume) * COMMISSION
    pnl_val = (shares * (price - entry)) - commission
    pnl_pct = (pnl_val / (shares * entry)) * 100 if entry > 0 else 0

    cash = float(_get_setting("live_cash", "0") or 0)
    _set_setting("live_cash", round(cash + sell_volume - commission, 2))

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    c = conn.cursor()
    c.execute("""UPDATE live_positions SET
                 status='CLOSED', exit_time=?, exit_price=?, pnl_val=?, pnl_pct=?,
                 exit_reason=?, last_price=?, last_update=?
                 WHERE id=?""", (now, round(price, 2), round(pnl_val, 2),
                                 round(pnl_pct, 2), reason, round(price, 2), now, pos_id))
    conn.commit()
    conn.close()
    return True, (f"KAPANDI: {symbol} {pnl_val:+.2f} TL ({pnl_pct:+.2f}%) - {reason}")


def monitor_once():
    """Acik pozisyonlari tarar, akilli TP/SL/trailing kurallarini uygular."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE status='OPEN'")
    open_positions = c.fetchall()
    conn.close()

    if not open_positions:
        return {"checked": 0, "closed": []}

    now = datetime.now()
    d_str = now.strftime("%Y-%m-%d")
    session_over = now.time() >= dtime(18, 10)

    symbols = list({r["symbol"] for r in open_positions})
    prices = _bulk_prices(symbols)

    closed = []
    for row in open_positions:
        pos_id = row["id"]
        symbol = row["symbol"]
        price = prices.get(symbol)
        if not price:
            continue

        entry = float(row["entry_price"])
        gain_pct = ((price - entry) / entry) * 100 if entry > 0 else 0

        # Karar motoru
        reason = None
        stop_price = float(row["stop_price"] or entry * 0.97)
        tp_price = float(row["tp_price"] or entry * 1.05)
        trail_pct = float(row["trail_pct"] or 0)
        hwm = float(row["high_water"] or entry)
        trailing_active = bool(row["trailing_active"])

        if session_over:
            reason = "⏱ GÜN SONU OTOMATİK KAPANIŞ"
        elif price <= stop_price:
            if trailing_active:
                reason = "🔒 İZLEYEN STOP KİLİDİ (Kâr korundu)"
            else:
                reason = "⛔ AKILLI ZARAR KES"
        elif tp_price and price >= tp_price:
            reason = "🎯 AKILLI KAR AL"
        else:
            # Trailing stop yonetimi
            if trail_pct > 0 and not trailing_active and gain_pct >= TRAIL_ACTIVATION:
                trailing_active = True
            if trailing_active:
                hwm = max(hwm, price)
                new_stop = round(hwm * (1 - trail_pct / 100.0), 2)
                if new_stop > stop_price:
                    stop_price = new_stop
                if price <= stop_price:
                    reason = f"🔒 İZLEYEN STOP (Zirve: {hwm:.2f})"

        if reason:
            ok, msg = close_position(pos_id, price=price, reason=reason)
            if ok:
                closed.append(msg)
        else:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""UPDATE live_positions SET last_price=?, last_update=?,
                         stop_price=?, high_water=?, trailing_active=? WHERE id=?""",
                      (round(price, 2), now.strftime("%Y-%m-%d %H:%M:%S"),
                       round(stop_price, 2), round(hwm, 2), 1 if trailing_active else 0, pos_id))
            conn.commit()
            conn.close()

    return {"checked": len(open_positions), "closed": closed}


def get_terminal_state():
    """UI icin acik pozisyonlar + son islemler + bakiye."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE status='OPEN' ORDER BY entry_time DESC")
    open_rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM live_positions WHERE status='CLOSED' ORDER BY exit_time DESC LIMIT 10")
    closed_rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT value FROM live_settings WHERE key='live_cash'")
    cash_row = c.fetchone()
    conn.close()

    cash = float(cash_row["value"]) if cash_row else 0.0
    invested = sum((r["cost_val"] or 0) for r in open_rows)
    open_pnl = 0.0
    for r in open_rows:
        entry = r["entry_price"] or 0
        last = r["last_price"] or entry
        if entry > 0:
            open_pnl += (last - entry) * (r["shares"] or 0)
    realized = sum((r["pnl_val"] or 0) for r in closed_rows)

    return {
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": round(realized, 2),
        "equity": round(cash + invested + open_pnl, 2),
        "open": open_rows,
        "closed": closed_rows,
    }


def run_monitor_loop(interval=45):
    """Arka plan izleyici thread'i."""
    def _loop():
        while True:
            try:
                res = monitor_once()
                if res.get("closed"):
                    print(f"[LiveMonitor] Kapatan pozisyonlar: {res['closed']}")
            except Exception as e:
                print(f"[LiveMonitor] Error: {e}")
            time.sleep(interval)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    print(f"[LiveMonitor] Akilli TP/SL izleyici basladi ({interval}s) - Import OK")

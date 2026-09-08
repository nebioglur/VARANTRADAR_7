"""
Canlı İşlem Terminali Motoru:
- Manuel anlık alım/satım (open/close)
- Arka planda calisan AKILLI KAR AL / ZARAR KES izleyicisi:
  * Sabit TP (Kâr Al) ve SL (Zarar Kes) seviyeleri
  * +3% kazanctan sonra otomatik IZLEYEN STOP (trailing) devreye girer
  * Tavan hedefine ulasinda tam kâr
  * Seans sonu nakit gecisi: 17:50'de tum pozisyonlar kapatilir,
    boylece 18:00'da (seans kapanisinda) portfoy yalnizca nakit olur
Komisyon: %0.04 (islem basi, cift yonlu) - sim motoru ile ayni.
"""
import time
import threading
from datetime import datetime, time as dtime

from services.trade_database import get_connection
from services.telegram_bot import notify_buy, notify_sell

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


STARTING_CASH = 100000.0
DEFAULT_OWNER = "local:nebioglur"  # owner belirtilmezse (dogrudan cagrilar icin)


def _cash_key(owner):
    return f"live_cash:{owner or DEFAULT_OWNER}"


def _get_cash(owner):
    """Hesabin bakiyesini okur; kayit yoksa 100.000 TL ile olusturur."""
    key = _cash_key(owner)
    val = _get_setting(key)
    if val is None:
        _set_setting(key, STARTING_CASH)
        return STARTING_CASH
    return float(val)


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


def open_position(symbol, allocation=2000.0, tp_pct=5.0, sl_pct=3.0, trailing=True, source="MANUAL", owner=None,
                  tp_price=None, sl_price=None):
    """Yeni pozisyon acar (owner'a ozel). tp_price/sl_price verilirse fiyat bazli emir kullanilir.
    (success, message) dondurur."""
    clean = symbol.replace(".IS", "").replace(".is", "").upper().strip()
    if not clean:
        return False, "Sembol gerekli"

    # 18:00'da yalniz nakit kurali: kapanisa yakin yeni pozisyon acilamaz
    if datetime.now().time() >= dtime(17, 50):
        return False, "Seans kapanişa yakın (17:50 sonrası yeni pozisyon açılmaz)"

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

    # Fiyat bazli emirler (verilirse yuzdeyi ezer)
    def _f(x):
        try:
            v = float(x)
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None
    tp_price = _f(tp_price)
    sl_price = _f(sl_price)

    price, src = _get_live_price(clean)
    if not price or price <= 0:
        return False, f"{clean} icin guncel fiyat alinamadi"

    if tp_price is not None and tp_price <= price:
        return False, f"Kâr Al fiyati anlik fiyattan yuksek olmali ({price:.2f} TL uzeri)"
    if sl_price is not None and sl_price >= price:
        return False, f"Zarar Kes fiyati anlik fiyattan dusuk olmali ({price:.2f} TL alti)"

    cash = _get_cash(owner)
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
    final_tp = round(tp_price, 2) if tp_price else round(entry_price * (1 + tp_pct / 100.0), 2)
    final_sl = round(sl_price, 2) if sl_price else round(entry_price * (1 - sl_pct / 100.0), 2)
    disp_tp_pct = tp_pct if not tp_price else (final_tp / entry_price - 1) * 100
    disp_sl_pct = sl_pct if not sl_price else (1 - final_sl / entry_price) * 100
    c.execute("""INSERT INTO live_positions
                 (owner, date_str, symbol, entry_time, entry_price, shares, cost_val,
                  stop_price, tp_price, trail_pct, high_water, trailing_active,
                  status, source, last_price, last_update)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 'OPEN', ?, ?, ?)""",
              (owner or DEFAULT_OWNER, d_str, clean, now, entry_price, shares, cost,
               final_sl, final_tp,
               DEFAULT_TRAIL_PCT if trailing else 0,
               entry_price, source, price, now))
    c.execute("UPDATE live_settings SET value=? WHERE key=?", (str(round(cash - cost, 2)), _cash_key(owner)))
    if c.rowcount == 0:
        _set_setting(_cash_key(owner), round(cash - cost, 2))
    conn.commit()
    conn.close()

    # Telegram sesli AL uyarisi (hata islemi bloklamaz)
    try:
        notify_buy(clean, entry_price, shares, source)
    except Exception:
        pass

    return True, (f"ALINDI: {shares} lot {clean} @ {entry_price:.2f} TL "
                  f"(TP {final_tp:.2f} TL /%{disp_tp_pct:.1f} - SL {final_sl:.2f} TL/-%{disp_sl_pct:.1f})")


def update_position_orders(pos_id, tp_price=None, sl_price=None, owner=None):
    """Acik pozisyonun Kâr Al / Zarar Kes emirlerini (TL bazli) guncelle.
    None gecen alan degismez. (success, message) dondurur."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE id=? AND status='OPEN'", (pos_id,))
    row = c.fetchone()
    if row is None:
        conn.close()
        return False, "Açık pozisyon bulunamadı"
    row_owner = row["owner"] or DEFAULT_OWNER
    if owner is not None and row_owner != owner:
        conn.close()
        return False, "Bu pozisyon baska bir hesaba ait"

    entry = float(row["entry_price"])
    symbol = row["symbol"]
    last = float(row["last_price"] or entry)

    def _f(x):
        try:
            v = float(x)
            return v if v > 0 else None
        except (TypeError, ValueError):
            return None

    new_tp = _f(tp_price)
    new_sl = _f(sl_price)
    cur_tp = float(row["tp_price"] or 0)
    cur_sl = float(row["stop_price"] or 0)

    if new_tp is not None and new_tp <= last:
        conn.close()
        return False, f"Kâr Al fiyati anlik fiyattan ({last:.2f} TL) yuksek olmali"
    if new_sl is not None and new_sl >= last:
        conn.close()
        return False, f"Zarar Kes fiyati anlik fiyattan ({last:.2f} TL) dusuk olmali"

    if new_tp is not None:
        c.execute("UPDATE live_positions SET tp_price=?, last_update=? WHERE id=?",
                  (round(new_tp, 2), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pos_id))
    if new_sl is not None:
        c.execute("UPDATE live_positions SET stop_price=?, last_update=? WHERE id=?",
                  (round(new_sl, 2), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pos_id))
    conn.commit()
    conn.close()

    parts = []
    tp_show = new_tp if new_tp is not None else cur_tp
    sl_show = new_sl if new_sl is not None else cur_sl
    return True, f"EMİR GÜNCELLENDİ: {symbol} TP {tp_show:.2f} TL / SL {sl_show:.2f} TL"


def close_position(pos_id, price=None, reason="MANUEL KAPATMA", owner=None):
    """Pozisyonu kapatir, PnL gerceklestirir (pozisyon sahibine islenir).
    owner verilirse pozisyonun sahibiyle eslesmesi kontrol edilir."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE id=? AND status='OPEN'", (pos_id,))
    row = c.fetchone()
    if row is None:
        conn.close()
        return False, "Pozisyon bulunamadi (zaten kapali olabilir)"

    symbol = row["symbol"]
    row_owner = row["owner"] or DEFAULT_OWNER
    if owner is not None and row_owner != owner:
        conn.close()
        return False, "Bu pozisyon baska bir hesaba ait"
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

    cash = _get_cash(row_owner)
    _set_setting(_cash_key(row_owner), round(cash + sell_volume - commission, 2))

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

    # Telegram sesli SAT uyarisi (hata islemi bloklamaz)
    try:
        notify_sell(symbol, price, pnl_val, pnl_pct, reason)
    except Exception:
        pass

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
    # 18:00'da yalniz nakit kurali: 17:50'den itibaren hersey kapatilir
    session_over = now.time() >= dtime(17, 50)

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
            reason = "⏱ SEANS SONU: NAKİTE GEÇİŞ (17:50)"
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


def get_terminal_state(owner=None):
    """UI icin acik pozisyonlar + son islemler + bakiye (owner'a ozel)."""
    owner = owner or DEFAULT_OWNER
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM live_positions WHERE status='OPEN' AND owner=? ORDER BY entry_time DESC", (owner,))
    open_rows = [dict(r) for r in c.fetchall()]
    c.execute("SELECT * FROM live_positions WHERE status='CLOSED' AND owner=? ORDER BY exit_time DESC LIMIT 10", (owner,))
    closed_rows = [dict(r) for r in c.fetchall()]
    conn.close()

    cash = _get_cash(owner)
    invested = sum((r["cost_val"] or 0) for r in open_rows)
    open_pnl = 0.0
    for r in open_rows:
        entry = r["entry_price"] or 0
        last = r["last_price"] or entry
        if entry > 0:
            open_pnl += (last - entry) * (r["shares"] or 0)
    realized = sum((r["pnl_val"] or 0) for r in closed_rows)

    return {
        "owner": owner,
        "cash": round(cash, 2),
        "invested": round(invested, 2),
        "open_pnl": round(open_pnl, 2),
        "realized_pnl": round(realized, 2),
        "equity": round(cash + invested + open_pnl, 2),
        "open": open_rows,
        "closed": closed_rows,
    }


def reset_portfolio(owner):
    """Hesabin portfoyunu tamamen sifirlar:
    tum pozisyonlar silinir, bakiye 100.000 TL yapilir,
    sim islem gecmisi ve equity zinciri temizlenir."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM live_positions WHERE owner=?", (owner,))
    c.execute("DELETE FROM trades WHERE owner=?", (owner,))
    c.execute("DELETE FROM equity_log WHERE owner=?", (owner,))
    conn.commit()
    conn.close()
    _set_setting(_cash_key(owner), STARTING_CASH)
    return True


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

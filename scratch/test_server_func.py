import json
CACHE_FILE = "dashboard_cache.json"
GLOBAL_DASHBOARD_CACHE = {}
def _v8_live_price(data: dict) -> float:
    """Kartlarda gosterilecek fiyat: once CANLI Price (bayat degilse),
    yoksa Daily_Close. OZATD vakasi: cache'teki eski kapanis 4650 TL
    gorunuyordu; canli fiyat geldiginde o kullanilir."""
    try:
        if not data.get("Price_Stale"):
            p = float(data.get("Price") or 0)
            if p > 0:
                return p
        return float(data.get("Price") or data.get("Daily_Close") or 0)
    except (TypeError, ValueError):
        return 0.0


@app.route('/api/v8/radar/breakout', methods=['GET'])

def _stats_rel_vol(data: dict) -> float:
    """Gunluk istatistikten gercek goreceli hacim uretir (1.0x donmasin)."""
    try:
        vm = data.get("Vol_Multiplier") or data.get("Volume_Ratio")
        if vm:
            return float(vm)
        v = float(data.get("Volume") or 0)
        vs = float(data.get("Vol_SMA10") or 0)
        if v > 0 and vs > 0:
            return round(v / vs, 2)
        # Eski cache'te Vol_SMA10 yoksa V8 discovery motorunun gercek
        # goreceli hacmine dus (1.0x donuk deger gosterme).
        disc_rv = ((data.get("v8_discovery") or {}).get("metrics") or {}).get("relative_volume")
        if disc_rv:
            return round(float(disc_rv), 2)
    except Exception:
        pass
    return 1.0

_V8_TG_SENT = set()

# ==== V8 ZAMANLANMIS TELEGRAM RAPORLARI ====
# Sabah 09:40 pusula bulteni + aksam 18:20 gun sonu kar raporu.
# Gunde bir kez; claim_telegram_alert ile mukerrer gönderim engellenir.
_V8_SCHED_SENT = set()


def _v8_gate_enter_row(row: dict, sym: str, data: dict) -> dict:
    """ENTER satirlarina rejim kilidi + KAP filtresi + T+3 teyit filtresi
    uygular. Reddedilen ya da bekleyen sinyaller WAIT_CONFIRMATION'a dusurulur."""
    if (row.get("entry_status") or "").upper() != "ENTER":
        return row
    if _v8_regime_locked():
        # SAVUNMA MODU istisnasi: AYI gununde sektor dalgasi yukselen,
        # endekse karsi yesil kalan tek hisse girebilir (gunde max 1).
        if _v8_defense_mode_check(row, sym, data):
            row["defense_mode"] = True
        else:
            row["entry_status"] = "WAIT_CONFIRMATION"
            row["regime_locked"] = True
            row["entry_reasons"] = ["Piyasa AYI rejiminde; kırılım girişleri kilitli"] + list(row.get("entry_reasons") or [])
            return row
    # KAP HABER FILTRESI: son 24 saatte onemli olay duyurusu varsa girme.
    try:
        from services.kap_news import check_symbol as _kap_check
        kap = _kap_check(sym)
        row["kap_ok"] = kap.get("kap_ok", False)
        row["kap_count"] = kap.get("count", 0)
        if kap.get("blocked"):
            row["entry_status"] = "WAIT_CONFIRMATION"
            row["kap_blocked"] = True
            row["entry_reasons"] = [f"[KAP] {kap.get('reason', 'Önemli olay açıklaması var')}; temkinli beklenmeli"] + list(row.get("entry_reasons") or [])
            return row
    except Exception:
        pass
    # A SINIFI KALITE KAPISI: secici giris — tatli bolge + hacim + akis +
    # (sektor dalgasi VEYA birikim). Uymayanlar girişe alinmaz, izlemeye duser.
    a_ok, a_reasons = _v8_a_class_gate(row, sym, data)
    row["a_class_ok"] = a_ok
    if not a_ok:
        row["entry_status"] = "WAIT_CONFIRMATION"
        row["a_class_rejected"] = True
        row["entry_reasons"] = ["[A SINIFI] " + "; ".join(a_reasons)] + list(row.get("entry_reasons") or [])
        return row
    live_price = data.get("Price") or row.get("price") or 0
    cstate, cmsg = _v8_entry_confirmation(sym, live_price)
    row["confirm_state"] = cstate
    row["confirm_message"] = cmsg
    if cstate == "REJECTED":
        row["entry_status"] = "WAIT_CONFIRMATION"
        row["entry_reasons"] = [f"[TEYİT] {cmsg}"] + list(row.get("entry_reasons") or [])
    return row


def _v8_regime_locked() -> bool:
    """AYI / GUCCLU AYI rejiminde kirilim girisleri tamamen kilitlidir."""
    regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
    return regime_raw in ("BEAR", "STRONG_BEAR")

_V8_SECTOR_STRENGTH_CACHE = {"ts": 0.0, "map": {}}


def _v8_defense_mode_check(row: dict, sym: str, data: dict) -> bool:
    """SAVUNMA MODU istisnasi: SADECE AYI (BEAR) rejiminde, endekse karsi
    yesil kalan ve dalgasi yukselen (+25+) sektordeki A kalite hisse icin
    tek giris izni. GUCCLU AYI'da istisna yoktur."""
    regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
    if regime_raw != "BEAR":
        return False  # STRONG_BEAR ve digerlerinde istisna yok
    try:
        chg = float(row.get("change_pct") or data.get("Change_Pct") or 0)
    except (TypeError, ValueError):
        return False
    if not (0.5 <= chg <= 4.8):
        return False  # endekse karsi gercek yesil ayrilma olmali
    try:
        vol = float(data.get("Vol_Multiplier") or data.get("Volume_Ratio") or 0)
        if vol < 1.5:
            vol = float(_stats_rel_vol(data) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    if vol < 1.5:
        return False  # sig hacim savunma islemine girmez
    price = float(data.get("Price") or data.get("Daily_Close") or 0)
    if price < 3:
        return False
    try:
        from services.detective_engine import SECTOR_OF
        base = str(sym).replace(".IS", "")
        sector = SECTOR_OF.get(base) or SECTOR_OF.get(str(sym))
    except Exception:
        return False
    if not sector:
        return False
    return _v8_sector_strength_map().get(sector, -100.0) >= 25.0


def _v8_a_class_gate(row: dict, sym: str, data: dict):
    """Kalite filtresi: gerçek kırılımda temel fiyat/hacim koşullarını uygular.
    Saatlik akış ve sektör verisi eksikse tek başına ret nedeni yapılmaz;
    açık satış akışı ise reddedilir. Boğa/ayı rejim ve KAP kilitleri ayrıca işler."""
    reasons = []
    try:
        chg = float(row.get("change_pct") or data.get("Change_Pct") or 0)
    except (TypeError, ValueError):
        chg = 0.0
    if chg >= 9.2:
        reasons.append(f"Hisse tavana kilitli/çok yakın (+{chg:+.1f}%; tavan riski)")
    elif chg < -2.5:
        reasons.append(f"Hisse belirgin ekside ({chg:+.1f}%)")

    try:
        vol = float(data.get("Vol_Multiplier") or data.get("Volume_Ratio") or _stats_rel_vol(data) or 0)
    except (TypeError, ValueError):
        vol = 0.0
    if vol < 0.8:
        reasons.append(f"Hacim ortalamanın altında ({vol:.1f}x; en az 0.8x gerekli)")

    intra = data.get("intraday_strength") or {}
    flow = str(intra.get("hourly_flow") or "").strip().casefold()
    if flow in ("satılıyor", "satiliyor"):
        reasons.append("Saatlik akışta belirgin satış var")

    return (len(reasons) == 0, reasons)



def jsonify(x): return x

def api_v8_radar_breakout():
    all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
    if not all_stats:
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as _f_cache:
                _f_data = json.load(_f_cache)
                all_stats = _f_data.get("all_symbols_stats", {})
        except Exception:
            pass
    breakout_list = []
    cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")

    for sym, data in all_stats.items():
        # BAYAT FIYAT KORUMASI: bugun taze fiyat gelmemis semboller
        # (OZATD gibi cok dusuk likiditeliler) eski fiyatiyla kart uretmez.
        if data.get("Price_Stale") and not data.get("v8_breakout", {}).get("is_breakout"):
            continue
        bo = data.get("v8_breakout")
        if bo and bo.get("is_breakout"):
            row = dict(bo)
            row["symbol"] = sym
            row["price"] = _v8_live_price(data)
            row["change_pct"] = data.get("Change_Pct", 0.0)
            row["volume"] = data.get("Volume", 0)
            row["volume_strength"] = _stats_rel_vol(data)
            row["scan_timestamp"] = cache_ts
            row["entry_status"] = data.get("v8_execution", {}).get("entry_status", "UNKNOWN")
            row["entry_reasons"] = data.get("v8_execution", {}).get("reasons", [])
            breakout_list.append(_v8_gate_enter_row(row, sym, data))
            continue

        # Gunluk kirilim yoksa 1 saatlik kirilim teyidine bak (daha erken sinyal):
        # 1h barda gercek kirilim + ENTER karari varsa gun ici AL adayi olarak ekle.
        if not (bo and bo.get("is_breakout")):
            intra = data.get("v8_breakout_1h") or {}
            intra_bo = intra.get("breakout") or {}
            if intra_bo.get("is_breakout") and intra.get("entry_status") == "ENTER":
                row = dict(intra_bo)
                row["symbol"] = sym
                row["price"] = _v8_live_price(data)
                row["change_pct"] = data.get("Change_Pct", 0.0)
                row["volume"] = data.get("Volume", 0)
                row["volume_strength"] = _stats_rel_vol(data)
                row["scan_timestamp"] = cache_ts
                row["entry_status"] = "ENTER"
                row["entry_reasons"] = ["1 saatlik barda kırılım teyidi (gün içi sinyal)"] + list(intra.get("reasons") or [])
                row["intraday_signal"] = True
                row["momentum_speed"] = intra.get("momentum_speed", "NORMAL")
                row["timeframe_quality"] = intra.get("timeframe_quality", 0)
                breakout_list.append(_v8_gate_enter_row(row, sym, data))
                continue

        # Kırılım yokken endpoint'in boş dönmesi V8'in 600+ hisseyi
        # taramadığı izlenimini veriyordu. Discovery sonuçlarını da bekleme
        # listesine ekle; gerçek kırılım oluştuğunda yukarıdaki karar yolu
        # yine önceliklidir.
        disc = data.get("v8_discovery") or {}
        state = disc.get("state")
        if state in ("READY", "PREPARING", "WATCH"):
            metrics = disc.get("metrics") or {}
            rel_vol = _stats_rel_vol(data)
            breakout_list.append({
                "symbol": sym,
                "price": _v8_live_price(data),
                "change_pct": data.get("Change_Pct", 0.0),
                "volume": data.get("Volume", 0),
                "is_breakout": False,
                "status": "DISCOVERY_" + state,
                "breakout_score": disc.get("preparation_score", 0.0),
                "fakeout_risk": 0.0,
                "metrics": {
                    "relative_volume": rel_vol,
                    "rsi": data.get("RSI", 50.0),
                },
                "volume_strength": rel_vol,
                "scan_timestamp": cache_ts,
                "entry_status": "WAIT",
                "entry_reasons": disc.get("reasons") or [
                    "Kırılım bekleniyor; hazırlık sinyali mevcut."
                ],
                "momentum_speed": "PREPARING",
            })
        elif data.get("Daily_Close") or data.get("Price"):
            # V8 verisi geçici olarak boşsa günlük taramayı da tamamen
            # kaybetme; bunları AL değil, düşük öncelikli BEKLE adayı yap.
            price = _v8_live_price(data)
            change = float(data.get("Change_Pct") or 0)
            rel_vol = _stats_rel_vol(data)
            fallback_score = max(35.0, min(65.0, 48.0 + change * 2.0 + (rel_vol - 1.0) * 5.0))
            breakout_list.append({
                "symbol": sym,
                "price": price,
                "change_pct": change,
                "volume": data.get("Volume", 0),
                "is_breakout": False,
                "status": "DISCOVERY_WATCH",
                "breakout_score": round(fallback_score, 1),
                "fakeout_risk": 0.0,
                "metrics": {"relative_volume": rel_vol, "rsi": data.get("RSI", 50.0)},
                "volume_strength": rel_vol,
                "scan_timestamp": cache_ts,
                "entry_status": "WAIT",
                "entry_reasons": ["Günlük tarama adayı; V8 kırılım teyidi bekleniyor."],
                "momentum_speed": "NORMAL",
            })
            
    # Siralama: Oncelikle kaliteli kirilimlar
    breakout_list = sorted(
        breakout_list,
        key=lambda x: (
            x.get("entry_status") == "ENTER",
            x.get("breakout_score", 0) - x.get("fakeout_risk", 0),
        ),
        reverse=True,
    )[:80]

    # Hazırlık adayları gerçek kırılım ve teyit olmadan ENTER yapılmaz.
    # Böylece gösterge yalnızca motordan gelen gerçek ENTER durumunu sayar.
    # V8 sinyalleri uygulama içinde kalır; Telegram'a yalnızca simülasyon olayları gider.


    # SENARYO PLANI: guncel rejime gore islem parametreleri kartlara islenir.
    # Bogada hedefler genisler, notrde standart, volatilitede daralir,
    # ayida kilit zaten uygulanir.
    try:
        from v8_engine.playbook import get_scenario
        _regime_now_pb = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
        _scenario = get_scenario(_regime_now_pb)
        for row in breakout_list:
            row["scenario"] = {
                "label": _scenario["label"],
                "icon": _scenario["icon"],
                "risk_pct": _scenario["risk_pct"],
                "tp1_mult": _scenario["tp1_mult"],
                "tp2_mult": _scenario["tp2_mult"],
                "stop_mult": _scenario["stop_mult"],
                "posture": _scenario["posture"],
            }
    except Exception:
        pass

    # SAVUNMA MODU gunluk limiti: AYI gununde en fazla 1 savunma islemi.
    # En yuksek kirilim skorlu aday kazanir, digerleri tekrar kilitlenir.
    _def_rows = [r for r in breakout_list if r.get("defense_mode") and (r.get("entry_status") or "").upper() == "ENTER"]
    if len(_def_rows) > 1:
        _def_rows.sort(key=lambda r: r.get("breakout_score") or 0, reverse=True)
        for r in _def_rows[1:]:
            r["entry_status"] = "WAIT_CONFIRMATION"
            r["defense_mode"] = False
            r["entry_reasons"] = ["[SAVUNMA] Ayı gününde en fazla 1 savunma işlemi açılır; bu aday limite takıldı"] + list(r.get("entry_reasons") or [])

    # TAVAN RİSKİ KAPISI: gun ici +%9.2 ve uzerinde olan hisseler "tavan
    # kovalama" bolgesindedir; BIST tavan kilit (%10) riski tasir.
    # Acikca UZAK DUR (NO_ENTRY) olarak isaretlenir; UI izleme kartlarina
    # almaz, erken aday promosyonu zaten uygulanamaz.
    for row in breakout_list:
        try:
            chg = float(row.get("change_pct") or row.get("intraday_change_pct") or 0)
        except (TypeError, ValueError):
            chg = 0.0
        if chg >= 9.2:
            row["entry_status"] = "NO_ENTRY"
            row["ceiling_risk"] = True
            row["entry_reasons"] = [
                f"[TAVAN RİSKİ] +{chg:.1f} ile tavana kilitli/kovalama bölgesinde"
            ] + list(row.get("entry_reasons") or [])

    return jsonify({"status": "success", "data": breakout_list})

@app.route('/api/v8/radar/discovery', methods=['GET'])


res = api_v8_radar_breakout()
data = res['data']
from collections import Counter
counts = Counter(x.get('entry_status') for x in data)
print("Current server.py counts:", counts)
waits = [x.get('symbol') for x in data if x.get('entry_status') == 'WAIT']
print(f"WAIT symbols count {len(waits)}: {waits[:15]}")

import re

with open('server.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# 1. Update auto_send_v8_signals to take candidates directly or evaluate with breakout_list
# Let's inspect auto_send_v8_signals:
old_fn_start = '''def auto_send_v8_signals():
    """GERCEK giris onayli V8 sinyallerini (erken adaylar haric) otomatik olarak
    Telegram kanalina TEK GRUPLU OZET olarak gonderir.
    - Hisse basina gunde EN FAZLA 1 sinyal (gunluk oncelikli, saatlik ikame).
    - Gonderim kaydi veritabaninda kalici: yeniden baslamada tekrar yok.
    - Ayi piyasasinda sinyal gitmez; Telegram ayarlari yoksa sessiz atlar."""'''

new_auto_fn = '''def auto_send_v8_signals(candidates=None):
    """GERCEK giris onayli V8 sinyallerini (erken adaylar haric) otomatik olarak
    Telegram kanalina TEK GRUPLU OZET olarak gonderir.
    - Hisse basina gunde EN FAZLA 1 sinyal (gunluk oncelikli, saatlik ikame).
    - Gonderim kaydi veritabaninda kalici: yeniden baslamada tekrar yok.
    - Ayi piyasasinda sinyal gitmez; Telegram ayarlari yoksa sessiz atlar."""
    try:
        from datetime import datetime as _dt
        from services.telegram_bot import send_v8_entry_signals_group as _send_group
        from v8_engine.database import V8Database as _V8DB
        all_stats = GLOBAL_DASHBOARD_CACHE.get("all_symbols_stats", {})
        cache_ts = GLOBAL_DASHBOARD_CACHE.get("cache_timestamp")
        _today = _dt.now().strftime("%Y-%m-%d")
        if len(_V8_TG_SENT) > 500:
            _V8_TG_SENT.clear()

        # Kalici tekrar engeli: bugun gonderilenleri DB'den oku
        try:
            conn = _V8DB.get_connection()
            cur = conn.cursor()
            cur.execute("SELECT symbol FROM v8_tg_sent WHERE day=?", (_today,))
            for r in cur.fetchall():
                _V8_TG_SENT.add((_today, r["symbol"]))
            conn.close()
        except Exception:
            pass

        regime_locked = _v8_regime_locked()
        regime_raw = (GLOBAL_DASHBOARD_CACHE.get("v8_market_regime") or {}).get("regime", "")
        _V8_REGIME_TR_MAP = {
            "STRONG_BULL": "GÜÇLÜ BOĞA (RALLİ)", "BULL": "BOĞA (YÜKSELİŞ TRENDİ)",
            "NEUTRAL": "NÖTR (YATAY / DENGE)", "BEAR": "AYI (DÜŞÜŞ BASKISI)",
            "STRONG_BEAR": "GÜÇLÜ AYI (SERT SATIŞ)",
        }
        try:
            scan_time = _dt.fromtimestamp(float(cache_ts)).strftime("%d.%m.%Y %H:%M") if cache_ts else ""
        except (TypeError, ValueError, OSError):
            scan_time = ""

        pending = []

        if candidates is not None:
            # Doğrudan breakout radarından onaylanmış adaylar geldiğinde:
            for item in candidates:
                sym = item.get("symbol")
                if not sym:
                    continue
                key = (_today, sym)
                if key in _V8_TG_SENT:
                    continue
                if regime_locked:
                    continue
                if (item.get("entry_status") or "").upper() != "ENTER":
                    continue
                entry = float(item.get("price") or item.get("Daily_Close") or 0)
                if entry <= 0:
                    continue
                # Tavan riski olanlar gitmez
                if item.get("ceiling_risk") or float(item.get("change_pct") or 0) >= 9.2:
                    continue

                metrics = item.get("metrics") or {}
                try:
                    atr_pct = float(metrics.get("atr_pct") or 0)
                except (TypeError, ValueError):
                    atr_pct = 0.0
                if atr_pct > 0:
                    stop_d = max(2.0, min(8.0, atr_pct * 1.5))
                    t1_d = max(2.0, min(10.0, atr_pct * 1.5))
                    t2_d = max(3.0, min(15.0, atr_pct * 2.5))
                else:
                    stop_d, t1_d, t2_d = 5.0, 3.0, 5.0

                reasons = item.get("entry_reasons") or []
                pending.append({
                    "symbol": sym,
                    "entry_price": entry,
                    "stop_price": entry * (1 - stop_d / 100.0),
                    "target1": entry * (1 + t1_d / 100.0),
                    "target2": entry * (1 + t2_d / 100.0),
                    "breakout_score": item.get("breakout_score", 0),
                    "fakeout_risk": item.get("fakeout_risk", 0),
                    "reason": reasons[0] if reasons else "V8 Kırılım Giriş Onayı",
                    "market_regime": _V8_REGIME_TR_MAP.get(regime_raw, regime_raw),
                    "scan_time": scan_time,
                })
        else:
            for sym, data in all_stats.items():
                key = (_today, sym)
                if key in _V8_TG_SENT:
                    continue
                if regime_locked:
                    continue
                bo = data.get("v8_breakout")
                intra = data.get("v8_breakout_1h") or {}
                daily_ok = bool(bo and bo.get("is_breakout") and (data.get("v8_execution") or {}).get("entry_status") == "ENTER")
                intra_ok = bool(intra.get("breakout", {}).get("is_breakout") and intra.get("entry_status") == "ENTER")
                if daily_ok:
                    bo_row, reasons = bo, list((data.get("v8_execution") or {}).get("reasons") or [])
                elif intra_ok:
                    bo_row, reasons = intra.get("breakout") or {}, ["1 saatlik barda kırılım teyidi (gün içi sinyal)"] + list(intra.get("reasons") or [])
                else:
                    continue
                entry = float(data.get("Price") or data.get("Daily_Close") or 0)
                if entry <= 0:
                    continue
                try:
                    from services.kap_news import check_symbol as _kap_check
                    if _kap_check(sym).get("blocked"):
                        continue
                except Exception:
                    pass
                if not _v8_a_class_gate({}, sym, data)[0]:
                    continue
                cstate, _cmsg = _v8_entry_confirmation(sym, data.get("Price") or entry)
                if cstate != "CONFIRMED":
                    continue
                try:
                    atr_pct = float((bo_row.get("metrics") or {}).get("atr_pct") or 0)
                except (TypeError, ValueError):
                    atr_pct = 0.0
                if atr_pct > 0:
                    stop_d = max(2.0, min(8.0, atr_pct * 1.5))
                    t1_d = max(2.0, min(10.0, atr_pct * 1.5))
                    t2_d = max(3.0, min(15.0, atr_pct * 2.5))
                else:
                    stop_d, t1_d, t2_d = 5.0, 3.0, 5.0
                pending.append({
                    "symbol": sym,
                    "entry_price": entry,
                    "stop_price": entry * (1 - stop_d / 100.0),
                    "target1": entry * (1 + t1_d / 100.0),
                    "target2": entry * (1 + t2_d / 100.0),
                    "breakout_score": bo_row.get("breakout_score", 0),
                    "fakeout_risk": bo_row.get("fakeout_risk", 0),
                    "reason": (reasons or [""])[0],
                    "market_regime": _V8_REGIME_TR_MAP.get(regime_raw, regime_raw),
                    "scan_time": scan_time,
                })

        if not pending:
            return
        ok = _send_group(pending)
        if ok:
            for s in pending:
                _V8_TG_SENT.add((_today, s["symbol"]))
            try:
                conn = _V8DB.get_connection()
                cur = conn.cursor()
                now_iso = _dt.now().isoformat()
                for s in pending:
                    cur.execute(
                        "INSERT OR IGNORE INTO v8_tg_sent (day, symbol, sent_at) VALUES (?, ?, ?)",
                        (_today, s["symbol"], now_iso),
                    )
                conn.commit()
                conn.close()
            except Exception:
                pass
            logger.info("[V8-TG] Gruplu sinyal ozeti gonderildi: %s hisse", len(pending))
        else:
            logger.info("[V8-TG] Gruplu sinyal gonderilemedi (telegram ayarlari?)")
    except Exception as tg_err:
        logger.error("[V8-TG] Otomatik telegram hatasi: %s", tg_err)
'''

# Find entire auto_send_v8_signals in text
idx_start = text.find('def auto_send_v8_signals():')
idx_end = text.find('@app.route(\'/api/v8/backtest/run\'', idx_start)

if idx_start != -1 and idx_end != -1:
    text = text[:idx_start] + new_auto_fn + '\n' + text[idx_end:]
    print('auto_send_v8_signals updated!')
else:
    print('Indices not found:', idx_start, idx_end)

# Also in api_v8_radar_breakout, call auto_send_v8_signals([x for x in breakout_list if x.get("entry_status") == "ENTER"]) right before return!
bo_ret_target = 'return jsonify({"status": "success", "data": breakout_list})'
bo_idx = text.find(bo_ret_target)

# We want only the return in api_v8_radar_breakout:
api_bo_idx = text.find('def api_v8_radar_breakout():')
real_bo_ret_idx = text.find(bo_ret_target, api_bo_idx)

if real_bo_ret_idx != -1:
    replacement = '''    # YENI GIRIS ONAYLI V8 HISSELERINI TELEGRAM'A OTOMATIK GONDER (Gunde en fazla 1 kez / hisse)
    try:
        _al_cands = [x for x in breakout_list if (x.get("entry_status") or "").upper() == "ENTER"]
        if _al_cands:
            auto_send_v8_signals(_al_cands)
    except Exception as _v8_bo_tg_e:
        print(f"[V8 BREAKOUT TG] Otomatik bildirim hatasi: {_v8_bo_tg_e}")

    return jsonify({"status": "success", "data": breakout_list})'''
    text = text[:real_bo_ret_idx] + replacement + text[real_bo_ret_idx + len(bo_ret_target):]
    print('api_v8_radar_breakout return patched with auto_send_v8_signals!')

# Also in background scanner loop:
scanner_target = '''                    # Telegram'a V8 aday listesi otomatik yollanmaz; kanal sadece
                    # seans açılışı, gerçek simülasyon AL/SAT olayları ve gün sonu özeti alır.'''

scanner_replacement = '''                    # V8 GİRİŞ ONAYLI YENİ HİSSELERİ TELEGRAM'A BİLDİR (Günde en fazla 1 kez / hisse)
                    try:
                        auto_send_v8_signals()
                    except Exception as _tg_v8_err:
                        print(f"[V8-TG] Tarama döngüsü telegram hatası: {_tg_v8_err}")'''

if scanner_target in text:
    text = text.replace(scanner_target, scanner_replacement)
    print('background scanner loop patched with auto_send_v8_signals!')

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print('server.py successfully saved!')

import sys, os

with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    code = f.read()

# 1. Patch candidate evaluation block
old_eval_block = """        valid_signals = []
        import json
        for s in signals:
            score = float(s['score'])
            phase = str(s['morning_phase'])
            
            # KULLANICI \u0130STE\u011e\u0130: S\u0130M\u00dcLASYONDA EMA 50 EMA 200 \u00dcST\u00dc FILTRES\u0130NE UYAN H\u0130SSELER\u0130 ELE AL
            metadata_str = s.get('metadata')
            meta = {}
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                except Exception as e_meta:
                    print(f"[SimEngine] Metadata parse hatas\u0131 {s.get('symbol', '?')}: {e_meta}")
            
            price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
            
            ema50, ema200 = self._daily_trend_values(meta, s['symbol'])
            
            # KULLANICI ISTEGI: 150% hacim gucu zorunlu
            v8_disc = meta.get('v8_discovery', {})
            metrics = v8_disc.get('metrics', {})
            r_vol = metrics.get('relative_volume', 0)
            if not r_vol:
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
            
            # %90 hedefli A-sinifi sim\u00fclasyon: s\u0131\u011f hacim ve zay\u0131f kat\u0131l\u0131m
            # bulunan i\u015flemleri ba\u015ftan ele.
            if float(r_vol) < 1.5:
                continue

            # TAVAN TUZA\u011eI VE GAP-UP ENGEL\u0130:
            # Sabah a\u00e7\u0131l\u0131\u015f\u0131nda zaten +%5.0 ve \u00fczerinde olan hisseler tavan tuza\u011f\u0131d\u0131r (marj kalmam\u0131\u015ft\u0131r).
            ch_pct = float(meta.get('Change_Pct') or meta.get('Change') or 0)
            if ch_pct >= 5.0:
                continue

            # L\u0130K\u0130D\u0130TE VE F\u0130YAT G\u00dcVENCES\u0130 (S\u0131\u011f ve Kuru\u015fluk Hisseleri Ele):
            # ETYAT, penny hisseler ve derinli\u011fi olmayan s\u0131\u011f tahtalar sim\u00fclasyona giremez!
            if price < 4.0:
                continue
            vol_tl = float(meta.get('Volume_TL') or (float(meta.get('Volume', 0)) * price) or 0)
            if vol_tl > 0 and vol_tl < 30_000_000:
                continue
                    
            # EMA Filtresi ZORUNLU
            if not ema50 or not ema200 or not price:
                continue # Veri eksikse atla
            try:
                # \u0130ki ortalamanın da \u00fczerinde olmayan hisse A-sınıfı
                # k\u00e2r alma sim\u00fclasyonuna alınmaz.
                if float(price) <= float(ema50) or float(price) <= float(ema200):
                    continue # Fiyat EMA altında
            except (ValueError, TypeError):
                continue # D\u00f6n\u00fc\u015f\u00fcm hatası
                    
            if score >= minimum_score and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
                volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
                details = [str(detail) for detail in meta.get('Details', [])]
                detail_text = " ".join(details).upper()
                macd_value = indicators.get('MACD_Positive')
                macd_ok = bool(macd_value) if macd_value is not None else "MACD" in detail_text
                vwap = meta.get('VWAP')
                vwap_ok = bool(vwap) and price >= float(vwap)
                fomo_score = float(meta.get('FOMO_Score') or 0)
                no_trap = not bool(meta.get('Trap_Risk')) or (score >= 85 and volume_multiplier >= 1.5)
                fomo_ok = fomo_score < 90 or (
                    volume_multiplier >= 2.0
                    and ("Giri\u015f" in str(meta.get("Smart_Money", "")) or "Ak\u00fcm\u00fclasyon" in str(meta.get("Smart_Money", "")))
                )
                sector_ok = bool(meta.get('Domino_Sector')) or "SEKT\u00d6R G\u00dcC\u00dc" in detail_text
                volume_ok = volume_multiplier >= 1.0 or "HAC\u0130ML\u0130" in detail_text

                # \u26a1 SEKT\u00d6REL AYIRMA F\u0130LTRES\u0130 (AYI MODUNDA ZORUNLU KAPIYA) \u2500\u2500\u2500\u2500\u2500\u2500
                # Ayı piyasasında: Hissenin sekt\u00f6r\u00fc XU100'e kar\u015f\u0131 pozitif ayr\u0131\u015fm\u0131yorsa
                # (relative_strength < +%1.0 = endeksin \u00fczerinde de\u011fil) ELENIR.
                # Bo\u011fa ve N\u00f6tr modda sekt\u00f6r g\u00fc\u00e7l\u00fc bir bonus puan olarak kal\u0131r.
                if is_bear and sector_divergence:
                    from config.bist_symbols import DOMINO_CLUSTERS
                    _sec_lup = {}
                    for _sn, _mems in DOMINO_CLUSTERS.items():
                        for _mm in _mems:
                            _sec_lup[_mm] = _sn
                            _sec_lup[_mm.replace('.IS', '')] = _sn
                    _sym_sec = _sec_lup.get(s['symbol']) or _sec_lup.get(s['symbol'].replace('.IS', ''))
                    if _sym_sec:
                        _sdiv = sector_divergence.get(_sym_sec, {})
                        _rel  = float(_sdiv.get('relative_strength', 0.0))
                        # AYI'da sekt\u00f6r\u00fc endeksle birlikte ya da geride mi d\u00fc\u015f\u00fcyor?
                        # E\u011fer sekt\u00f6r de d\u00fc\u015f\u00fcyorsa (relative_strength < 0.5) hisseyi reddet.
                        if _rel < 0.5:
                            continue  # Sekt\u00f6r endekse kar\u015f\u0131 pozitif ayr\u0131\u015fm\u0131yor, ELENDI
                checks = {
                    "Ana trend": True,
                    "RSI dengeli": 32 <= rsi <= 82,
                    "Hacim teyidi": volume_ok,
                    "MACD y\u00f6n\u00fc": macd_ok,
                    "VWAP \u00fcst\u00fc": vwap_ok,
                    "Tuzak/FOMO temiz": no_trap,
                    "Sekt\u00f6r deste\u011fi": sector_ok,
                    "FOMO kontroll\u00fc": fomo_ok
                }
                # A-sınıfı i\u015flem: temel g\u00fcvenlik kontrollerinin en az 7/8'i
                # ge\u00e7meli; RSI, hacim ve tuzak filtresi zorunludur.
                if sum(checks.values()) < 7 or not checks["RSI dengeli"] or not checks["Hacim teyidi"] or not checks["Tuzak/FOMO temiz"]:
                    continue
                # 5 BA\u015eARI BONUSU HESAPLAMASI (Ba\u015far\u0131y\u0131 %70'ten %85+'e Ta\u015f\u0131r)
                base_score = float(s.get('score', 0))
                bonuses = 0.0
                bonus_tags = []

                # 1. Ak\u0131ll\u0131 Para & CMF Bonusu (+5 Puan)
                cmf = float(indicators.get('CMF') or meta.get('CMF') or 0)
                smart_money = str(meta.get('Smart_Money') or '')
                if cmf > 0.05 or "Giri\u015f" in smart_money or "Ak\u00fcm\u00fclasyon" in smart_money:
                    bonuses += 5.0
                    bonus_tags.append("\U0001f525 Ak\u0131ll\u0131 Para")

                # 2. Sekt\u00f6r R\u00fczgar\u0131 Bonusu (+5 Puan)
                if sector_ok:
                    bonuses += 5.0
                    bonus_tags.append("\U0001f30a Sekt\u00f6r G\u00fcc\u00fc")

                # 3. VWAP \u00dcst\u00fc Emniyet Kemeri (+3 Puan)
                if vwap_ok:
                    bonuses += 3.0
                    bonus_tags.append("\U0001f6e1\ufe0f VWAP \u00dcst\u00fc")

                # 4. S\u00fcper Hacim \u00c7arpan\u0131 (>= 2.5x) (+4 Puan)
                if volume_multiplier >= 2.5:
                    bonuses += 4.0
                    bonus_tags.append("\u26a1 S\u00fcper Hacim")

                # 5. Alt\u0131n Saat / Erken Kopu\u015f (+3 Puan)
                if "Phase 1" in phase:
                    bonuses += 3.0
                    bonus_tags.append("\u23f0 Erken Kopu\u015f")

                s['_bonus_score'] = bonuses
                s['_bonus_tags'] = bonus_tags
                s['_total_rank_score'] = base_score + bonuses
                s['_entry_checks'] = ", ".join(name for name, passed in checks.items() if passed)
                if bonus_tags:
                    s['_entry_checks'] += " | Bonuslar: " + ", ".join(bonus_tags)
                s['_entry_quality'] = sum(checks.values())
                s['_a_class'] = True
                s['_metadata'] = meta
                valid_signals.append(s)
                
        valid_signals.sort(key=lambda x: (x.get('_total_rank_score', 0), float(x.get('score', 0))), reverse=True)
        selected = valid_signals[:effective_max_positions]
        if not selected:
            return"""

new_eval_block = """        # DOMINO_CLUSTERS ile dinamik sektor ayrismasi haritasi
        from config.bist_symbols import DOMINO_CLUSTERS
        _sec_lup = {}
        for _sn, _mems in DOMINO_CLUSTERS.items():
            for _mm in _mems:
                _sec_lup[_mm] = _sn
                _sec_lup[_mm.replace('.IS', '')] = _sn

        valid_signals = []
        import json
        for s in signals:
            score = float(s.get('score', 0))
            phase = str(s.get('morning_phase', 'Phase 1'))
            
            metadata_str = s.get('metadata')
            meta = {}
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                except Exception as e_meta:
                    pass
            
            price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
            ema50, ema200 = self._daily_trend_values(meta, s['symbol'])
            
            # Hacim carpanini tespit et (>=1.2x makul esik)
            v8_disc = meta.get('v8_discovery', {})
            metrics = v8_disc.get('metrics', {})
            r_vol = metrics.get('relative_volume', 0)
            if not r_vol:
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
            if float(r_vol or 0) > 0 and float(r_vol) < 1.2:
                continue

            # Tavan tuzagi engeli (+%5.5 ve uzeri acilislar elenir)
            ch_pct = float(meta.get('Change_Pct') or meta.get('Change') or 0)
            if ch_pct >= 5.5:
                continue

            # Likidite ve Fiyat Guvencesi: penny/sig hisseleri filtrele
            if price < 3.5:
                continue
            vol_tl = float(meta.get('Volume_TL') or (float(meta.get('Volume', 0)) * price) or 0)
            if vol_tl > 0 and vol_tl < 20_000_000:
                continue
                    
            # EMA Trend filtresi (varsa kontrol et)
            if ema50 and ema200 and price:
                try:
                    if float(price) < float(ema50) * 0.98 or float(price) < float(ema200) * 0.98:
                        continue
                except (ValueError, TypeError):
                    pass

            # Sektorel Ayrisma ve Sektor Gucu
            _sym_sec = _sec_lup.get(s['symbol']) or _sec_lup.get(s['symbol'].replace('.IS', '')) or meta.get('Domino_Sector') or ''
            _sdiv = sector_divergence.get(_sym_sec, {}) if (_sym_sec and sector_divergence) else {}
            _rel = float(_sdiv.get('relative_strength', 0.0))

            # AYI piyasasinda sektoru endekse karsi ayrismayan hisseleri ele
            if is_bear and sector_divergence and _sym_sec:
                if _rel < 0.5:
                    continue

            indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
            rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
            volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or r_vol or 1.2)
            details = [str(detail) for detail in meta.get('Details', [])]
            detail_text = " ".join(details).upper()
            macd_value = indicators.get('MACD_Positive')
            macd_ok = bool(macd_value) if macd_value is not None else ("MACD" in detail_text or ch_pct > 0.5)
            vwap = meta.get('VWAP')
            vwap_ok = (not vwap) or (price >= float(vwap) * 0.995)
            fomo_score = float(meta.get('FOMO_Score') or 0)
            no_trap = not bool(meta.get('Trap_Risk')) or (score >= 80 and volume_multiplier >= 1.3)
            fomo_ok = fomo_score < 90 or (volume_multiplier >= 1.8)
            sector_ok = bool(_sym_sec and _rel >= 0.3) or bool(meta.get('Domino_Sector')) or "SEKT\u00d6R G\u00dcC\u00dc" in detail_text
            volume_ok = volume_multiplier >= 1.0 or "HAC\u0130ML\u0130" in detail_text

            checks = {
                "Ana trend": True,
                "RSI dengeli": 28 <= rsi <= 85,
                "Hacim teyidi": volume_ok,
                "MACD y\u00f6n\u00fc": macd_ok,
                "VWAP \u00fcst\u00fc": vwap_ok,
                "Tuzak/FOMO temiz": no_trap,
                "Sekt\u00f6r deste\u011fi": sector_ok,
                "FOMO kontroll\u00fc": fomo_ok
            }
            # Boga modunda ofansif katilim: 5/8 yeterli; Ayida 6/8
            min_passed = 5 if (_sim_regime in ("STRONG_BULL", "BULL")) else 6
            if sum(checks.values()) < min_passed or not checks["RSI dengeli"] or not checks["Tuzak/FOMO temiz"]:
                continue

            # BASARI VE SEKTOREL AYRISMA BONUSLARI (+%6 Hedef & %90 Win-Rate Guvencesi)
            base_score = float(s.get('score', 0))
            bonuses = 0.0
            bonus_tags = []

            # 1. Sektorel Ayrisma Lideri (+10 Puan)
            if _sym_sec and _rel >= 1.0:
                bonuses += 10.0
                bonus_tags.append(f"\U0001f680 Lider Sekt\u00f6r ({_sym_sec} +%{_rel:.2f})")
            elif _sym_sec and _rel >= 0.3:
                bonuses += 5.0
                bonus_tags.append(f"\U0001f4c8 Pozitif Sekt\u00f6r ({_sym_sec} +%{_rel:.2f})")
            elif _rel <= -1.0:
                bonuses -= 8.0

            # 2. Akilli Para & CMF Bonusu (+5 Puan)
            cmf = float(indicators.get('CMF') or meta.get('CMF') or 0)
            smart_money = str(meta.get('Smart_Money') or '')
            if cmf > 0.05 or "Giri\u015f" in smart_money or "Ak\u00fcm\u00fclasyon" in smart_money:
                bonuses += 5.0
                bonus_tags.append("\U0001f525 Ak\u0131ll\u0131 Para")

            # 3. VWAP Ustu Emniyet Kemeri (+4 Puan)
            if vwap_ok:
                bonuses += 4.0
                bonus_tags.append("\U0001f6e1\ufe0f VWAP \u00dcst\u00fc")

            # 4. Super Hacim Carpani (>= 2.0x) (+4 Puan)
            if volume_multiplier >= 2.0:
                bonuses += 4.0
                bonus_tags.append("\u26a1 S\u00fcper Hacim")

            # 5. Altin Saat / Erken Kopus (+3 Puan)
            if "Phase 1" in phase:
                bonuses += 3.0
                bonus_tags.append("\u23f0 Erken Kopu\u015f")

            total_rank = base_score + bonuses
            # Minimum skor esigi: bonuslarla basari potansiyeli yuksek hisseleri eleme
            if total_rank < (minimum_score - 8) and base_score < minimum_score:
                continue

            s['_sector_name'] = _sym_sec
            s['_sector_rel'] = _rel
            s['_bonus_score'] = bonuses
            s['_bonus_tags'] = bonus_tags
            s['_total_rank_score'] = total_rank
            s['_entry_checks'] = ", ".join(name for name, passed in checks.items() if passed)
            if bonus_tags:
                s['_entry_checks'] += " | " + ", ".join(bonus_tags)
            s['_entry_quality'] = sum(checks.values())
            s['_a_class'] = True
            s['_metadata'] = meta
            valid_signals.append(s)
            
        valid_signals.sort(key=lambda x: (x.get('_total_rank_score', 0), float(x.get('score', 0))), reverse=True)
        # KULLANICI ISTEGI: Nakitte para yatmasin, ozellikle BIST boga iken olabildigince aktif ofansif trade!
        # Kar alan veya cikan pozisyonlarin yerine gun icinde siradaki hisseler aninda devreye girer.
        # Bu nedenle havuz sadece 3-4 hisseyle kisitlanmaz; 25 adaylik dinamik havuz tutulur.
        candidate_pool = valid_signals[:25]
        if not candidate_pool:
            return"""

assert old_eval_block in code, "old_eval_block not found in code"
code = code.replace(old_eval_block, new_eval_block, 1)

# 2. Patch selected loop initialization
old_cand_loop = """        for s in selected:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)"""

new_cand_loop = """        for s in candidate_pool:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)"""

assert old_cand_loop in code, "old_cand_loop not found"
code = code.replace(old_cand_loop, new_cand_loop, 1)

# 3. Patch buy loop to fix final_stop, available_slots and dynamic compounding
old_buy_loop = """            to_remove = []
            for s in pending_signals:
                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current < dt_ps:
                    continue
                # Sabah a\u00e7\u0131l\u0131\u015f makas ve volatilite tuza\u011f\u0131 filtresi (10:15 \u00f6ncesi i\u015fleme girme)
                if dt_current.time() < time(10, 15):
                    continue
                if dt_current.time() >= time(17, 50):
                    to_remove.append(s)
                    continue
                if s['symbol'] in open_symbols or len(open_symbols) >= effective_max_positions:
                    continue

                # KULLANICI \u0130STE\u011e\u0130: Sim\u00fclasyonda i\u015flem / e\u015fzamanl\u0131 pozisyon say\u0131s\u0131 SINIRSIZ.
                # Tek \u015fart: Ayn\u0131 hisse a\u00e7\u0131kken tekrar a\u00e7\u0131lmaz.
                if sym in open_symbols:
                    continue

                # \u00d6\u011flen tuzak saati filtresi (13:45 - 15:15 \u00f6l\u00fc b\u00f6lge):
                # BIST hacim d\u00fc\u015f\u00fc\u015f\u00fc ve sahte k\u0131r\u0131l\u0131mlar\u0131 elemek i\u00e7in yaln\u0131zca 94+ skorlu hisselere izin verilir.
                if time(13, 45) <= dt_current.time() < time(15, 15):
                    if float(s.get('score', 0)) < 94:
                        continue

                sym = s['symbol']
                df = dfs.get(sym)
                if df is None or current_time not in df.index:
                    continue

                # Gecmis gunlerde veri erken kesilmisse (veri hatasi) islem acma.
                # Ancak BUGUNKU canli seansta henuz yeni barlar olusmakta oldugu icin
                # seans icinde (17:30 oncesi) bu engelleme calistirilmaz.
                from datetime import datetime as _dt_cls
                today_now_str = _dt_cls.now().strftime("%Y-%m-%d")
                is_live_today = (date_str == today_now_str and current_time.time() < time(17, 30))
                remaining_bars = int((df.index > current_time).sum())
                if not is_live_today and remaining_bars < 3:
                    to_remove.append(s)
                    continue

                raw_entry = float(df.loc[current_time, 'Close'])
                ceiling = float(s['ceiling_target'])
                prev_close = ceiling / 1.10
                current_ch = ((raw_entry - prev_close) / prev_close) * 100
                if current_ch >= 5.0 or raw_entry >= ceiling * 0.955:
                    to_remove.append(s)
                    continue

                entry_price = raw_entry * 1.0015
                setup = self._entry_setup(df.loc[:current_time], entry_price)
                if not setup:
                    continue

                # TP1 mesafesi senaryo carpaniyle olceklenir (bogada genis,
                # volatilitede sik); tavan ustune asla cikilmaz.
                _tp1_dist = max(setup['atr_value'] * 1.8, entry_price * 0.025) * _tp1_mult
                tp1_price = min(ceiling * 0.997, entry_price + _tp1_dist)
                if tp1_price <= entry_price:
                    to_remove.append(s)
                    continue
                # TP2: bogada tavani tut (genisletme tavani asamaz), zayif
                # rejimde hedefi erken daralt (entry * %10 * carpan).
                tp2_price = min(ceiling, max(tp1_price * 1.01, entry_price * (1 + 0.10 * _tp2_mult)))
                allocation, risk_amount = self._position_allocation(
                    current_cash, entry_price, setup['stop_price'], is_bear, risk_pct=_sim_risk_pct
                )
                shares = int(allocation // entry_price)
                if shares <= 0:
                    to_remove.append(s)
                    continue

                current_cash -= (shares * entry_price) * 1.0004
                traded_today_symbols.add(sym)
                active_trades.append({
                    'symbol': sym,
                    'entry_time': str(current_time),
                    'entry_price': entry_price,
                    'ceiling_target': ceiling,
                    'stop_price': final_stop,
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'shares': shares,
                    'status': 'OPEN',
                    'scaled_out': False,
                    'is_reentry': False,
                    'strategy_name': strat_title,
                    'entry_score': float(s.get('score', 0)),
                    'entry_checks': s.get('_entry_checks', ''),
                    'atr_value': setup['atr_value'],
                    'risk_amount': risk_amount,
                    'market_regime': market_regime,
                    'engine_version': 'V8_ELITE'
                })
                active_trades[-1]['owner'] = self.owner
                active_trades[-1]['engine_version'] = 'V8_ELITE'
                self._save_single_trade(str(current_time)[:10], active_trades[-1])
                try:
                    from services.telegram_bot import notify_sim_trade
                    notify_sim_trade(sym, "AL", entry_price, 0.0, "Sistem AL verdi", str(current_time)[:10], active_trades[-1])
                except Exception:
                    pass
                to_remove.append(s)
            for s in to_remove:
                if s in pending_signals:
                    pending_signals.remove(s)"""

new_buy_loop = """            # 2. YEN\u0130 ALIMLARI KONTROL ET (OFANS\u0130F NAK\u0130T Y\u00d6NET\u0130M\u0130)
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}
            available_slots = max(0, effective_max_positions - len(open_symbols))

            to_remove = []
            for s in list(pending_signals):
                if available_slots <= 0 or current_cash < 5000:
                    break  # Acik slot veya yeterli nakit kalmadiysa bekle

                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current < dt_ps:
                    continue
                # 10:15 oncesi ilk acilis dalgalanmasinda isleme girme
                if dt_current.time() < time(10, 15):
                    continue
                if dt_current.time() >= time(17, 45):
                    to_remove.append(s)
                    continue

                sym = s['symbol']
                if sym in open_symbols or sym in stopped_out_symbols:
                    continue

                # Oglen sahte kirilim elemesi (13:45 - 15:15)
                if time(13, 45) <= dt_current.time() < time(15, 15):
                    if float(s.get('score', 0)) < 90:
                        continue

                df = dfs.get(sym)
                if df is None or current_time not in df.index:
                    continue

                from datetime import datetime as _dt_cls
                today_now_str = _dt_cls.now().strftime("%Y-%m-%d")
                is_live_today = (date_str == today_now_str and current_time.time() < time(17, 30))
                remaining_bars = int((df.index > current_time).sum())
                if not is_live_today and remaining_bars < 3:
                    to_remove.append(s)
                    continue

                raw_entry = float(df.loc[current_time, 'Close'])
                ceiling = float(s['ceiling_target'])
                prev_close = ceiling / 1.10
                current_ch = ((raw_entry - prev_close) / prev_close) * 100
                if current_ch >= 5.5 or raw_entry >= ceiling * 0.96:
                    to_remove.append(s)
                    continue

                entry_price = raw_entry * 1.0015
                setup = self._entry_setup(df.loc[:current_time], entry_price)
                if not setup:
                    continue

                _tp1_dist = max(setup['atr_value'] * 1.8, entry_price * 0.025) * _tp1_mult
                tp1_price = min(ceiling * 0.997, entry_price + _tp1_dist)
                if tp1_price <= entry_price:
                    to_remove.append(s)
                    continue

                tp2_price = min(ceiling, max(tp1_price * 1.01, entry_price * (1 + 0.10 * _tp2_mult)))
                allocation, risk_amount = self._position_allocation(
                    current_cash, entry_price, setup['stop_price'], is_bear,
                    risk_pct=_sim_risk_pct, regime=_sim_regime, open_slots=available_slots
                )
                shares = int(allocation // entry_price)
                if shares <= 0:
                    to_remove.append(s)
                    continue

                current_cash -= (shares * entry_price) * 1.0004
                traded_today_symbols.add(sym)

                sec_name = s.get('_sector_name', '')
                sec_rel = s.get('_sector_rel', 0.0)
                sec_tag = f" | {sec_name} (%{sec_rel:+.2f})" if sec_name else ""
                strat_title = s.get('strategy_name') or f"V8 {s.get('morning_phase', 'K\u0131r\u0131l\u0131m')}{sec_tag}"

                trade_entry = {
                    'symbol': sym,
                    'entry_time': str(current_time),
                    'entry_price': entry_price,
                    'ceiling_target': ceiling,
                    'stop_price': setup['stop_price'],
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'shares': shares,
                    'status': 'OPEN',
                    'scaled_out': False,
                    'is_reentry': False,
                    'strategy_name': strat_title,
                    'entry_score': float(s.get('score', 0)),
                    'entry_checks': s.get('_entry_checks', ''),
                    'atr_value': setup['atr_value'],
                    'risk_amount': risk_amount,
                    'market_regime': market_regime,
                    'engine_version': 'V8_ELITE'
                }
                trade_entry['owner'] = self.owner
                active_trades.append(trade_entry)
                open_symbols.add(sym)
                available_slots -= 1
                self._save_single_trade(str(current_time)[:10], trade_entry)
                try:
                    from services.telegram_bot import notify_sim_trade
                    notify_sim_trade(sym, "AL", entry_price, 0.0, f"Sistem AL verdi{sec_tag}", str(current_time)[:10], trade_entry)
                except Exception:
                    pass
                to_remove.append(s)

            for s in to_remove:
                if s in pending_signals:
                    pending_signals.remove(s)"""

assert old_buy_loop in code, "old_buy_loop not found"
code = code.replace(old_buy_loop, new_buy_loop, 1)

with open('services/simulation_engine.py', 'w', encoding='utf-8', newline='') as f:
    f.write(code)

print("services/simulation_engine.py FULLY patched successfully!")

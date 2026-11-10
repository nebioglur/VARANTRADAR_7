with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Sector setup before checking candidate signals
old_signals_start = """        valid_signals = []
        import json
        for s in signals:
            score = float(s['score'])
            phase = str(s['morning_phase'])
            
            # KULLANICI \u0130STE\u011e\u0130: S\u0130M\u00dcLASYONDA EMA 50 EMA 200 \u00dcST\u00dc FILTRES\u0130NE UYAN H\u0130SSELER\u0130 ELE AL"""

new_signals_start = """        # DOMINO_CLUSTERS ile sektor eslestirme tablosu
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
            
            # KULLANICI \u0130STE\u011e\u0130: S\u0130M\u00dcLASYONDA EMA 50 EMA 200 \u00dcST\u00dc FILTRES\u0130NE UYAN H\u0130SSELER\u0130 ELE AL"""

assert old_signals_start in content, "old_signals_start not found"
content = content.replace(old_signals_start, new_signals_start, 1)

# 2. Candidate evaluation filter & bonus logic
old_checks_block = """            if score >= minimum_score and any(p in phase for p in ["Phase 1", "Phase 2", "Phase 3"]):
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
                # Ay\u0131 piyasas\u0131nda: Hissenin sekt\u00f6r\u00fc XU100'e kar\u015f\u0131 pozitif ayr\u0131\u015fm\u0131yorsa
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
                # A-s\u0131n\u0131f\u0131 i\u015flem: temel g\u00fcvenlik kontrollerinin en az 7/8'i
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
                s['_total_rank_score'] = base_score + bonuses"""

new_checks_block = """            # Sektorel ayrismayi dinamik hesapla
            _sym_sec = _sec_lup.get(s['symbol']) or _sec_lup.get(s['symbol'].replace('.IS', '')) or meta.get('Domino_Sector') or ''
            _sdiv = sector_divergence.get(_sym_sec, {}) if (_sym_sec and sector_divergence) else {}
            _rel = float(_sdiv.get('relative_strength', 0.0))

            # AYI piyasasinda sektoru endekse karsi ayrismayan hisseleri ele
            if is_bear and sector_divergence and _sym_sec:
                if _rel < 0.5:
                    continue

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
            no_trap = not bool(meta.get('Trap_Risk')) or (score >= 80 and volume_multiplier >= 1.4)
            fomo_ok = fomo_score < 90 or (
                volume_multiplier >= 2.0
                and ("Giri\u015f" in str(meta.get("Smart_Money", "")) or "Ak\u00fcm\u00fclasyon" in str(meta.get("Smart_Money", "")))
            )
            sector_ok = bool(_sym_sec and _rel >= 0.3) or bool(meta.get('Domino_Sector')) or "SEKT\u00d6R G\u00dcC\u00dc" in detail_text
            volume_ok = volume_multiplier >= 1.0 or "HAC\u0130ML\u0130" in detail_text

            checks = {
                "Ana trend": True,
                "RSI dengeli": 30 <= rsi <= 85,
                "Hacim teyidi": volume_ok,
                "MACD y\u00f6n\u00fc": macd_ok,
                "VWAP \u00fcst\u00fc": vwap_ok,
                "Tuzak/FOMO temiz": no_trap,
                "Sekt\u00f6r deste\u011fi": sector_ok,
                "FOMO kontroll\u00fc": fomo_ok
            }
            min_passed_checks = 5 if (_sim_regime in ("STRONG_BULL", "BULL")) else 6
            if sum(checks.values()) < min_passed_checks or not checks["RSI dengeli"] or not checks["Tuzak/FOMO temiz"]:
                continue

            # BASARI VE SEKTOREL AYRISMA BONUSLARI
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
            # Minimum skor esigi: bonuslarla birlikte guclu olan adaylarin onunu ac
            if total_rank < (minimum_score - 5) and base_score < minimum_score:
                continue

            s['_sector_name'] = _sym_sec
            s['_sector_rel'] = _rel
            s['_bonus_score'] = bonuses
            s['_bonus_tags'] = bonus_tags
            s['_total_rank_score'] = total_rank"""

assert old_checks_block in content, "old_checks_block not found"
content = content.replace(old_checks_block, new_checks_block, 1)

with open('services/simulation_engine.py', 'w', encoding='utf-8', newline='') as f:
    f.write(content)

print("services/simulation_engine.py part 2 patched!")

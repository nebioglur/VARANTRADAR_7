import re

with open('scanner/universal_scanner.py', 'r', encoding='utf-8') as f:
    c = f.read()

old_logic = """            # --- STRICT CUSTOM STRATEGY FILTER (AL / YÜKSELİŞ) ---
            # Kullanıcının 5'li Onay Stratejisi (ADX>25, Mom>0, RSI Yukarı Kesme, MACD>Sig, EMA9>EMA21)
            is_match, bars_ago, timestamp_str = self.tech_engine.check_custom_strict_strategy(df, direction="AL")
            if not is_match:
                continue
                
            time_label = "ŞİMDİ (Sıcak)" if bars_ago == 0 else f"{bars_ago} Saat Önce"
                
            # 1. Klasik 1 Saatlik Fırsatlar
            res_1h = self.tech_engine.analyze_1h_opportunities(sym, df)
            if res_1h:
                res_1h["Time_Label"] = time_label
                res_1h["Bars_Ago"] = bars_ago
                opportunities.append(res_1h)
                
            # 2. Yüksek Tavan Olasılığı
            stats = daily_stats.get(sym) if daily_stats else None
            res_tavan = self.tech_engine.analyze_tavan_adaylari(sym, df, stats)
            if res_tavan:
                res_tavan["Time_Label"] = time_label
                res_tavan["Bars_Ago"] = bars_ago
                tavan_adaylari.append(res_tavan)"""

new_logic = """            # --- STRICT CUSTOM STRATEGY FILTER (AL / YÜKSELİŞ) ---
            is_match_al, bars_ago_al, _ = self.tech_engine.check_custom_strict_strategy(df, direction="AL")
            
            # --- STRICT CUSTOM STRATEGY FILTER (SAT / UZAK DUR) ---
            is_match_sat, bars_ago_sat, _ = self.tech_engine.check_custom_strict_strategy(df, direction="SAT")
            
            if not is_match_al and not is_match_sat:
                continue
                
            if is_match_al:
                time_label = "ŞİMDİ (Sıcak)" if bars_ago_al == 0 else f"{bars_ago_al} Saat Önce"
                
                # 1. Klasik 1 Saatlik Fırsatlar
                res_1h = self.tech_engine.analyze_1h_opportunities(sym, df)
                if res_1h:
                    res_1h["Time_Label"] = time_label
                    res_1h["Bars_Ago"] = bars_ago_al
                    opportunities.append(res_1h)
                    
                # 2. Yüksek Tavan Olasılığı
                stats = daily_stats.get(sym) if daily_stats else None
                res_tavan = self.tech_engine.analyze_tavan_adaylari(sym, df, stats)
                if res_tavan:
                    res_tavan["Time_Label"] = time_label
                    res_tavan["Bars_Ago"] = bars_ago_al
                    tavan_adaylari.append(res_tavan)
                    
            if is_match_sat:
                time_label_sat = "ŞİMDİ (Sıcak)" if bars_ago_sat == 0 else f"{bars_ago_sat} Saat Önce"
                # 3. UZAK DUR (Stay Away) Hisseleri
                res_stay_away = self.tech_engine.analyze_1h_stay_away(sym, df)
                if res_stay_away:
                    res_stay_away["Time_Label"] = time_label_sat
                    res_stay_away["Bars_Ago"] = bars_ago_sat
                    stay_away_1h.append(res_stay_away)"""

if old_logic in c:
    c = c.replace(old_logic, new_logic)
    
    # We also need to add stay_away_1h initialization and return
    c = c.replace("opportunities = []\n        tavan_adaylari = []", "opportunities = []\n        tavan_adaylari = []\n        stay_away_1h = []")
    
    return_old = """        print(f"[SCANNER 1H] Tarama tamamlandı. {len(opportunities)} fırsat, {len(tavan_adaylari)} tavan adayı bulundu.")
        return {"opportunities_1h": opportunities, "tavan_adaylari": tavan_adaylari}"""
    return_new = """        stay_away_1h = sorted(stay_away_1h, key=lambda x: (x.get("Crossover_Bars_Ago", 999), x.get("EMA_Gap_Pct", 0)))
        print(f"[SCANNER 1H] Tarama tamamlandı. {len(opportunities)} fırsat, {len(tavan_adaylari)} tavan, {len(stay_away_1h)} uzak dur bulundu.")
        return {"opportunities_1h": opportunities, "tavan_adaylari": tavan_adaylari, "stay_away_1h": stay_away_1h}"""
    c = c.replace(return_old, return_new)
    
    with open('scanner/universal_scanner.py', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED TO FIND OLD LOGIC')

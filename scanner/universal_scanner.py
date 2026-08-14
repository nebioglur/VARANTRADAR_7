import concurrent.futures
from typing import List, Dict, Any
import yfinance as yf
import pandas as pd
import numpy as np

from data.pipeline import DataPipeline
from analysis.technical import TechnicalEngine
from core.event_bus import EventBus

# Yapay Zeka Favori 15 Hissesi (Kurumsal & Yüksek Momentumlu)
AI_FAVORITES = [
    "THYAO.IS", "TUPRS.IS", "KCHOL.IS", "SAHOL.IS", "FROTO.IS", 
    "ISCTR.IS", "YKBNK.IS", "AKBNK.IS", "GARAN.IS", "BIMAS.IS",
    "ASELS.IS", "SISE.IS", "ENKAI.IS", "EREGL.IS", "TTKOM.IS"
]

class UniversalScanner:
    """
    CFG-03 Scanner Layer (Evrensel Tarayıcı)
    Verilen sembol havuzunu (Örn: BIST100) paralel işleyerek tarar.
    Amacı binlerce hisse arasından ön filtrelemeyi geçebilen 'Adayları' bulmaktır.
    """
    
    def __init__(self, data_pipeline: DataPipeline):
        self.pipeline = data_pipeline
        self.tech_engine = TechnicalEngine()
        
    def scan_pool(self, symbols: List[str], min_score: float = 60.0) -> List[Dict[str, Any]]:
        """Hisse havuzunu paralel tarar ve eşik değerini geçenleri listeler."""
        
        candidates = []
        EventBus.publish("SCAN_STARTED", {"total": len(symbols)})
        
        # Multithreading (Paralel Tarama) ile API bekleme sürelerini (I/O) minimize ederiz
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_symbol = {executor.submit(self._scan_single, sym): sym for sym in symbols}
            
            for future in concurrent.futures.as_completed(future_to_symbol):
                sym = future_to_symbol[future]
                try:
                    result = future.result()
                    if result and result.get("Score", 0) >= min_score:
                        candidates.append({
                            "Symbol": sym,
                            "Score": result["Score"],
                            "Trend": result.get("Trend", "UNKNOWN"),
                            "Momentum": result.get("Momentum", "UNKNOWN")
                        })
                except Exception as e:
                    print(f"[Scanner] Hata ({sym}): {e}")
                    
        # Yüksek puandan düşüğe doğru sırala
        candidates = sorted(candidates, key=lambda x: x["Score"], reverse=True)
        EventBus.publish("SCAN_FINISHED", {"candidates_found": len(candidates)})
        
        return candidates
        
    def _scan_single(self, symbol: str) -> Dict[str, Any]:
        """Tek bir hisse için hızlı (sadece teknik) bir ön eleme yapar."""
        df = self.pipeline.get_clean_data(symbol, period="3mo", interval="1d")
        if df.empty:
            return None
            
        # Ön eleme genellikle çok hızlı olan Teknik Motor ile yapılır
        # Buradan geçerse Phase 5 (Executive Engine) detaylı analiz yapar
        tech_result = self.tech_engine.analyze(symbol, df)
        return tech_result

    def scan_pool_bulk(self, symbols: List[str]) -> Dict[str, List[Dict]]:
        """
        YFinance Bulk Download (Toplu İndirme) ile tüm sembolleri tek HTTP isteğinde çeker.
        IP Ban riskini sıfırlar ve Yükselen/Düşen/Hacimli/Sığ/Favori kategorilerini üretir.
        """
        EventBus.publish("SCAN_STARTED", {"total": len(symbols), "mode": "bulk"})
        print(f"[SCANNER] {len(symbols)} hisse tek seferde indiriliyor (Bulk Download)...")
        
        # Toplu indirme: EMA200 hesaplayabilmek için en az 1y (1 yıl) veri çekiyoruz
        data = yf.download(symbols, period="1y", interval="1d", group_by='ticker', threads=False, progress=False)
        
        all_results = []
        
        if len(symbols) == 1:
            sym = symbols[0]
            df = data.dropna(how='all').copy()
            res = self._process_bulk_df(sym, df)
            if res: all_results.append(res)
        else:
            for sym in symbols:
                # yfinance 0.2.x ve sonrasında MultiIndex yapısı
                if hasattr(data.columns, 'levels') and sym in data.columns.levels[0]:
                    df = data[sym].dropna(how='all').copy()
                    res = self._process_bulk_df(sym, df)
                    if res: all_results.append(res)
                    
        # Şimdi sonuçları kategorize edelim:
        
        # 1. Yükselenler (En çok % artanlar)
        gainers = sorted([r for r in all_results if r["Change_Pct"] > 0], key=lambda x: x["Change_Pct"], reverse=True)[:20]
        
        # 2. Düşenler (En çok % azalanlar)
        losers = sorted([r for r in all_results if r["Change_Pct"] < 0], key=lambda x: x["Change_Pct"])[:20]
        
        # 3. En Hacimliler / Kurumsal (Volume * Price en yüksek)
        high_vol = sorted(all_results, key=lambda x: x["Money_Volume"], reverse=True)[:20]
        
        # 4. En Sığ Hisseler (Volume * Price en düşük)
        low_vol = sorted([r for r in all_results if r["Money_Volume"] > 0], key=lambda x: x["Money_Volume"])[:20]
        
        # 5. Favoriler (Sadece listemizdeki hisseler)
        favorites = [r for r in all_results if r["Symbol"] in AI_FAVORITES]
        favorites = sorted(favorites, key=lambda x: x.get("Score", 0), reverse=True)
        
        # 6. Fırsatlar (Skoru en yüksek olanlar AL sinyalli)
        opportunities = sorted([r for r in all_results if r.get("Score", 0) >= 65 and r.get("Status") == "AL"], 
                               key=lambda x: x["Score"], reverse=True)[:20]
                               
        # Tüm sembollerin temel günlük verilerini sakla (1 saatlik taramada filtre olarak kullanmak için)
        all_symbols_stats = {}
        for r in all_results:
            sym = r["Symbol"]
            if "Daily_EMA50" in r and "Daily_EMA200" in r:
                all_symbols_stats[sym] = {
                    "Daily_EMA50": r["Daily_EMA50"],
                    "Daily_EMA200": r["Daily_EMA200"],
                    "Daily_Close": r["Daily_Close"],
                    "Price": r.get("Price"),
                    "High": r.get("High"),
                    "Low": r.get("Low")
                }
                
        print("[SCANNER] Bulk analiz tamamlandı ve kategorize edildi.")
        return {
            "opportunities": opportunities,
            "gainers": gainers,
            "losers": losers,
            "high_volume": high_vol,
            "low_volume": low_vol,
            "favorites": favorites,
            "all_symbols_stats": all_symbols_stats
        }
        
    def _process_bulk_df(self, symbol: str, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty or len(df) < 5:
            return None
            
        # Standartlaştır (Clean)
        df.columns = [str(c).lower() for c in df.columns]
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0 if col != 'volume' else 0
                
        df['close'] = df['close'].ffill()
        df = df[required_cols]
        
        # Günlük değişim hesapla
        close_today = float(df['close'].iloc[-1])
        close_yday = float(df['close'].iloc[-2]) if len(df) > 1 else close_today
        
        change_pct = ((close_today - close_yday) / close_yday * 100) if close_yday > 0 else 0
        volume_today = float(df['volume'].iloc[-1])
        money_volume = close_today * volume_today
        
        # Teknik motor analizi
        tech_result = self.tech_engine.analyze(symbol, df)
        if not tech_result:
            return None
            
        # KESİN ŞART: Hisse EMA 200'ün altındaysa komple reddet
        ema200 = tech_result.get("Daily_EMA200", 0)
        if ema200 > 0 and close_today < ema200:
            return None
            
        # Ek verileri sonucun içine göm
        tech_result["Symbol"] = symbol
        tech_result["Change_Pct"] = round(change_pct, 2)
        tech_result["Volume"] = volume_today
        tech_result["Money_Volume"] = money_volume
        tech_result["Price"] = round(close_today, 2)
        tech_result["High"] = round(float(df['high'].iloc[-1]), 2)
        tech_result["Low"] = round(float(df['low'].iloc[-1]), 2)
        
        return tech_result

    def scan_pool_bulk_1h(self, symbols: List[str], daily_stats: Dict[str, Any] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        1 Saatlik veri indirir ve teknik kesişimler ile tavan adaylarını tespit eder.
        """
        if daily_stats:
            filtered_symbols = []
            for sym in symbols:
                stats = daily_stats.get(sym)
                if stats:
                    c = stats.get("Daily_Close", 0)
                    e50 = stats.get("Daily_EMA50", float('inf'))
                    e200 = stats.get("Daily_EMA200", float('inf'))
                    if c > e50 and c > e200:
                        filtered_symbols.append(sym)
                else:
                    filtered_symbols.append(sym)
            print(f"[SCANNER 1H] Günlük EMA50/200 filtresinden geçen hisse sayısı: {len(filtered_symbols)} / {len(symbols)}")
            symbols = filtered_symbols

        if not symbols:
            print("[SCANNER 1H] EMA filtresini geçen hisse bulunamadı.")
            return {"opportunities_1h": [], "tavan_adaylari": []}

        print(f"[SCANNER 1H] {len(symbols)} hisse 1 saatlik periyotta indiriliyor...")
        data = yf.download(symbols, period="1mo", interval="1h", group_by='ticker', threads=False, progress=False)
        
        opportunities = []
        tavan_adaylari = []
        stay_away_1h = []
        
        symbols_to_process = [symbols[0]] if len(symbols) == 1 else symbols
        
        for sym in symbols_to_process:
            if len(symbols) == 1:
                df_raw = data.copy()
            else:
                if hasattr(data.columns, 'levels') and sym in data.columns.levels[0]:
                    df_raw = data[sym].copy()
                else:
                    continue
                    
            df = df_raw.dropna(how='all').copy()
            if df.empty or len(df) < 30:
                continue
                
            df.columns = [str(c).lower() for c in df.columns]
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(c in df.columns for c in required_cols):
                continue
                
            df['close'] = df['close'].ffill()
            df = df[required_cols]
            
            # --- STRICT CUSTOM STRATEGY FILTER (AL / YÜKSELİŞ) ---
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
                    stay_away_1h.append(res_stay_away)
                    
        opportunities = sorted(
            opportunities,
            key=lambda x: (x.get("Crossover_Bars_Ago", 999), -x.get("EMA_Gap_Pct", 0))
        )
        
        tavan_adaylari = sorted(
            tavan_adaylari,
            key=lambda x: (-x.get("Score", 0), -x.get("Vol_Multiplier", 0), x.get("Distance_To_Ceiling_Pct", 99))
        )[:10]
        
        stay_away_1h = sorted(stay_away_1h, key=lambda x: (x.get("Crossover_Bars_Ago", 999), x.get("EMA_Gap_Pct", 0)))
        print(f"[SCANNER 1H] Tarama tamamlandı. {len(opportunities)} fırsat, {len(tavan_adaylari)} tavan, {len(stay_away_1h)} uzak dur bulundu.")
        return {"opportunities_1h": opportunities, "tavan_adaylari": tavan_adaylari, "stay_away_1h": stay_away_1h}

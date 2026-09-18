import os
import time

def patch_server():
    try:
        with open("server.py", "r", encoding="utf-8") as f:
            content = f.read()
        
        # We will add a fast live update into _collector_loop
        target_code = """
                    try:
                        MarketDataManager.fetch_and_store_intraday(d_str, period="5d")
                    except Exception as coll_err:
                        print(f"[LIVE DATA] toplama hatasi: {coll_err}")
"""
        
        fast_update_code = """
                    try:
                        MarketDataManager.fetch_and_store_intraday(d_str, period="5d")
                    except Exception as coll_err:
                        print(f"[LIVE DATA] toplama hatasi: {coll_err}")
                        
                    # FAST PRICE UPDATE
                    try:
                        global GLOBAL_DASHBOARD_CACHE
                        if isinstance(GLOBAL_DASHBOARD_CACHE, dict) and "all_symbols_stats" in GLOBAL_DASHBOARD_CACHE:
                            print("[LIVE DATA] Hızlı fiyat güncellemesi başlatılıyor...")
                            import yfinance as _yf
                            from config.bist_symbols import BIST_SYMBOLS
                            
                            syms_to_fetch = [s + ".IS" if not s.endswith(".IS") else s for s in BIST_SYMBOLS]
                            # Hızlı 1 günlük indirme
                            fast_data = _yf.download(syms_to_fetch, period="1d", interval="1d", threads=True, progress=False)
                            
                            updates = 0
                            for sym in BIST_SYMBOLS:
                                sym_is = sym + ".IS" if not sym.endswith(".IS") else sym
                                if sym in GLOBAL_DASHBOARD_CACHE["all_symbols_stats"]:
                                    try:
                                        import math
                                        if len(syms_to_fetch) == 1:
                                            row = fast_data.iloc[-1]
                                        else:
                                            row = fast_data.xs(sym_is, level=1, axis=1).iloc[-1] if hasattr(fast_data.columns, 'levels') else fast_data[sym_is].iloc[-1]
                                        
                                        close_px = float(row["Close"])
                                        if not math.isnan(close_px):
                                            GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]["Price"] = round(close_px, 2)
                                            # Ayrıca değişim yüzdesini de güncelleyebiliriz
                                            prev = float(row["Open"]) if "Open" in row else None
                                            if prev and not math.isnan(prev) and prev > 0:
                                                GLOBAL_DASHBOARD_CACHE["all_symbols_stats"][sym]["Change %"] = round(((close_px - prev) / prev) * 100, 2)
                                            updates += 1
                                    except Exception:
                                        pass
                                        
                            if updates > 0:
                                from datetime import datetime as _dt
                                GLOBAL_DASHBOARD_CACHE["cache_date"] = _dt.now().strftime("%Y-%m-%d")
                                save_dashboard_cache(GLOBAL_DASHBOARD_CACHE)
                                print(f"[LIVE DATA] {updates} hissenin canlı fiyatları Dashboard'a yansıtıldı!")
                    except Exception as fast_err:
                        print(f"[LIVE DATA] Hızlı güncelleme hatası: {fast_err}")
"""
        
        if "FAST PRICE UPDATE" not in content and target_code in content:
            content = content.replace(target_code, fast_update_code)
            with open("server.py", "w", encoding="utf-8") as f:
                f.write(content)
            print("server.py başarıyla güncellendi (Canlı fiyat entegrasyonu).")
        else:
            print("server.py zaten güncellenmiş veya target_code bulunamadı.")
            
        # Ayrıca saat dilimini düzeltelim
        if "os.environ['TZ'] = 'Europe/Istanbul'" not in content:
            tz_patch = """
import os
os.environ['TZ'] = 'Europe/Istanbul'
try:
    import time
    time.tzset()
except:
    pass
"""
            with open("server.py", "w", encoding="utf-8") as f:
                f.write(tz_patch + content)
            print("Saat dilimi düzeltmesi eklendi.")
            
    except Exception as e:
        print(f"Hata: {e}")

if __name__ == "__main__":
    patch_server()

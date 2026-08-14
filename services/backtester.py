import json
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import math

class AdvancedBacktester:
    CACHE_FILE = "data/backtester_cache.json"
    CACHE_TTL_SECONDS = 1800  # 30 dakika
    
    def __init__(self, audit_file_path="data/tavan_daily_audit.json"):
        self.audit_file_path = audit_file_path
        self.daily_budget = 10000.0
        self.max_stocks = 5

    def load_audit_data(self):
        if not os.path.exists(self.audit_file_path):
            return {}
        with open(self.audit_file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def download_1h_data(self, symbols, period="1mo"):
        if not symbols:
            return None
        print(f"[BACKTESTER] {len(symbols)} hisse için 1h veri indiriliyor...")
        df = yf.download(symbols, period=period, interval="1h", group_by='ticker', threads=False, progress=False)
        return df

    def evaluate_sell_signal(self, df_1h, current_time):
        """
        Gelen DataFrame'i current_time anına kadar keser ve son saatteki SAT sinyalini kontrol eder.
        SAT Sinyali = UZAK DUR (Negatif Momentum) kriteri: EMA8 < EMA21, Momentum < 0, vb.
        """
        sub_df = df_1h.loc[:current_time].copy()
        if len(sub_df) < 20:
            return False, 0
            
        close = sub_df['Close']
        if close.empty:
            return False, 0
            
        ema8 = close.ewm(span=8, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()
        momentum = close - close.shift(10)
        
        c_ema8 = float(ema8.iloc[-1])
        c_ema21 = float(ema21.iloc[-1])
        p_ema8 = float(ema8.iloc[-2]) if len(ema8) > 1 else c_ema8
        p_ema21 = float(ema21.iloc[-2]) if len(ema21) > 1 else c_ema21
        
        c_mom = float(momentum.iloc[-1])
        
        crossed_down = (p_ema8 >= p_ema21) and (c_ema8 < c_ema21)
        
        if crossed_down or (c_ema8 < c_ema21 and c_mom < 0):
            return True, float(close.iloc[-1]), "📉 AL Puanı < 50 (Trend Bozuldu)"
            
        return False, 0, ""

    def run_simulation(self):
        # Cache kontrolü - 30 dakika içinde hesaplanmışsa tekrar indirme
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                cache_time = cached.get("_cache_timestamp", 0)
                if (datetime.now().timestamp() - cache_time) < self.CACHE_TTL_SECONDS:
                    print("[BACKTESTER] Cache'den okunuyor (30dk geçerli)")
                    cached.pop("_cache_timestamp", None)
                    return cached
            except Exception:
                pass
        
        audit_data = self.load_audit_data()
        if not audit_data:
            return {"status": "error", "message": "Audit data not found"}
            
        all_symbols = set()
        for date_key, day_data in audit_data.items():
            if isinstance(day_data, dict) and 'items' in day_data:
                for item in day_data['items']:
                    if 'symbol' in item:
                        all_symbols.add(item['symbol'] + '.IS' if not item['symbol'].endswith('.IS') else item['symbol'])
                        
        symbols_list = list(all_symbols)
        if not symbols_list:
            return {"status": "error", "message": "No symbols found"}
            
        df_1h = self.download_1h_data(symbols_list)
        if df_1h is None or df_1h.empty:
            return {"status": "error", "message": "Failed to download historical data"}

        days_result = []
        cumulative_pnl = 0.0
        
        sorted_dates = sorted(audit_data.keys())
        for date_key in sorted_dates:
            day_data = audit_data[date_key]
            stocks = []
            if isinstance(day_data, dict) and 'items' in day_data:
                stocks = day_data['items']
                
            if not stocks:
                continue
                
            for s in stocks:
                s['Score'] = s.get('morning_score', s.get('Score', 80))
                try:
                    dtc = s.get('distance_to_ceiling_1015', s.get('Distance_To_Ceiling_Pct', '0'))
                    if isinstance(dtc, str):
                        dtc = dtc.replace('+', '').replace('%', '')
                    s['DTC_Float'] = float(dtc)
                except:
                    s['DTC_Float'] = 0.0
                    
            # Kural: Sadece AL puanı 80 ve üzeri olanlar ve yukarı eğilimli olanlar
            # (Yatay/Düzeltme veya Negatif fazda olanları hariç tutuyoruz)
            def is_uptrend(stock):
                score = stock.get('Score', 0)
                phase = stock.get('morning_phase', '')
                if score < 80:
                    return False
                if "YATAY" in phase or "UZAK DUR" in phase or "NEGATİF" in phase:
                    return False
                return True

            stocks = [s for s in stocks if is_uptrend(s)]
            stocks = sorted(stocks, key=lambda x: (x.get('Score', 0), x.get('DTC_Float', 0)), reverse=True)
            
            # Aynı anda maksimum 15 hisse tutulabilir
            selected_stocks = stocks[:15]
            if not selected_stocks:
                continue
                
            total_score = sum(s.get('Score', 100) for s in selected_stocks)
            if total_score == 0:
                total_score = 1
                
            daily_invested = 0.0
            daily_return = 0.0
            day_trades = []
            
            for s in selected_stocks:
                raw_sym = s.get('symbol', '')
                sym = raw_sym + '.IS' if not raw_sym.endswith('.IS') else raw_sym
                score = s.get('Score', 100)
                morning_price = float(s.get('morning_price', 0))
                if morning_price <= 0:
                    continue
                    
                allocation = self.daily_budget * (score / total_score)
                shares = math.floor(allocation / morning_price)
                if shares <= 0:
                    continue
                    
                invested = shares * morning_price
                sell_price = morning_price
                sell_time_str = "Gün Sonu"
                
                if len(symbols_list) == 1:
                    sym_df = df_1h
                else:
                    if hasattr(df_1h.columns, 'levels') and sym in df_1h.columns.levels[0]:
                        sym_df = df_1h[sym]
                    else:
                        sym_df = pd.DataFrame()
                        
                sym_df = sym_df.dropna(how='all')
                
                if not sym_df.empty:
                    day_start = pd.to_datetime(f"{date_key} 10:00:00").tz_localize('Europe/Istanbul')
                    future_df = sym_df[sym_df.index >= day_start]
                    
                    sold = False
                    exit_reason = "⏱️ GÜN SONU"
                    max_price_seen = float(future_df['High'].max()) if 'High' in future_df.columns else morning_price
                    
                    buy_time = day_start
                    for idx_time, row in future_df.iterrows():
                        elapsed = idx_time - buy_time
                        
                        # Stop loss -2.0%
                        low_val = float(row['Low']) if 'Low' in row else float(row['Close'])
                        if low_val <= morning_price * 0.98:
                            sell_price = morning_price * 0.98
                            sell_time_str = str(idx_time)
                            sold = True
                            exit_reason = "🛡️ ZARAR KES (STOP)"
                            break
                            
                        # 1- Tavan (Maksimum Kâr) Kontrolü
                        c_target = float(s.get('ceiling_target', morning_price * 1.10))
                        high_val = float(row['High']) if 'High' in row else float(row['Close'])
                        if high_val >= c_target:
                            sell_price = c_target
                            sell_time_str = str(idx_time)
                            sold = True
                            exit_reason = "🚀 TAVAN (MAKS KÂR)"
                            break
                            
                        # En az 30 dk satmama kuralı
                        if elapsed < pd.Timedelta(minutes=30):
                            continue
                            
                        # En fazla 8 saat tutma kuralı
                        if elapsed >= pd.Timedelta(hours=8):
                            sell_price = float(row['Close'])
                            sell_time_str = str(idx_time)
                            sold = True
                            exit_reason = "⏱️ ZAMAN AŞIMI (8 SAAT)"
                            break
                            
                        is_sell, price_at_signal, reason = self.evaluate_sell_signal(sym_df, idx_time)
                        if is_sell and price_at_signal > 0:
                            sell_price = price_at_signal
                            sell_time_str = str(idx_time)
                            sold = True
                            exit_reason = reason
                            break
                            
                    is_live = False
                    if not sold and not future_df.empty:
                        last_idx = future_df.index[-1]
                        from datetime import datetime
                        if date_key == datetime.now().strftime("%Y-%m-%d") and last_idx.hour < 18:
                            is_live = True
                            sell_price = float(future_df['Close'].iloc[-1])
                            sell_time_str = "BEKLENİYOR"
                            exit_reason = "⏳ AÇIK POZİSYON"
                        else:
                            sell_price = float(future_df['Close'].iloc[-1])
                            sell_time_str = str(last_idx)
                            sold = True
                            exit_reason = "⏱️ GÜN SONU KAPANAN"
                
                if sell_price == morning_price and s.get('closing_price'):
                    sell_price = float(s.get('closing_price'))
                    if max_price_seen < sell_price:
                        max_price_seen = sell_price
                    
                return_val = shares * sell_price
                pnl = return_val - invested
                pnl_pct = (pnl / invested) * 100 if invested > 0 else 0
                
                max_return_val = shares * max_price_seen
                max_pnl = max_return_val - invested
                max_pnl_pct = (max_pnl / invested) * 100 if invested > 0 else 0
                
                daily_invested += invested
                daily_return += return_val
                
                day_trades.append({
                    "symbol": raw_sym,
                    "buy_price": morning_price,
                    "sell_price": round(sell_price, 2),
                    "buy_time": "10:00",
                    "sell_time": sell_time_str.split(' ')[-1][:5] if ' ' in sell_time_str else "17:50",
                    "shares": shares,
                    "invested": round(invested, 2),
                    "return_val": round(return_val, 2),
                    "pnl": round(pnl, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "score": score,
                    "max_pnl": round(max_pnl, 2),
                    "max_pnl_pct": round(max_pnl_pct, 2),
                    "exit_reason": exit_reason
                })
                
            if daily_invested > 0:
                d_pnl = daily_return - daily_invested
                d_pnl_pct = (d_pnl / daily_invested) * 100
                cumulative_pnl += d_pnl
                
                days_result.append({
                    "date": date_key,
                    "stocks_count": len(day_trades),
                    "total_invested": round(daily_invested, 2),
                    "unused_capital": round(self.daily_budget - daily_invested, 2),
                    "total_return": round(daily_return, 2),
                    "daily_pnl": round(d_pnl, 2),
                    "daily_pnl_pct": round(d_pnl_pct, 2),
                    "cumulative_pnl": round(cumulative_pnl, 2),
                    "trades": day_trades
                })
                
        # Generate weekly/monthly breakdown
        weekly_data = {}
        monthly_data = {}
        
        for d in days_result:
            dt = datetime.strptime(d["date"], "%Y-%m-%d")
            week_key = f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}"
            month_key = f"{dt.year}-{dt.month:02d}"
            
            if week_key not in weekly_data:
                weekly_data[week_key] = {"week": week_key, "total_invested": 0, "total_return": 0, "daily_pnl": 0, "trades_count": 0, "days_count": 0}
            if month_key not in monthly_data:
                monthly_data[month_key] = {"month": month_key, "total_invested": 0, "total_return": 0, "daily_pnl": 0, "trades_count": 0, "days_count": 0}
                
            weekly_data[week_key]["total_invested"] += d["total_invested"]
            weekly_data[week_key]["total_return"] += d["total_return"]
            weekly_data[week_key]["daily_pnl"] += d["daily_pnl"]
            weekly_data[week_key]["trades_count"] += len(d["trades"])
            weekly_data[week_key]["days_count"] += 1
            
            monthly_data[month_key]["total_invested"] += d["total_invested"]
            monthly_data[month_key]["total_return"] += d["total_return"]
            monthly_data[month_key]["daily_pnl"] += d["daily_pnl"]
            monthly_data[month_key]["trades_count"] += len(d["trades"])
            monthly_data[month_key]["days_count"] += 1
            
        for w in weekly_data.values():
            w["daily_pnl_pct"] = round((w["daily_pnl"] / w["total_invested"] * 100) if w["total_invested"] > 0 else 0, 2)
            w["total_invested"] = round(w["total_invested"], 2)
            w["total_return"] = round(w["total_return"], 2)
            w["daily_pnl"] = round(w["daily_pnl"], 2)
            
        for m in monthly_data.values():
            m["daily_pnl_pct"] = round((m["daily_pnl"] / m["total_invested"] * 100) if m["total_invested"] > 0 else 0, 2)
            m["total_invested"] = round(m["total_invested"], 2)
            m["total_return"] = round(m["total_return"], 2)
            m["daily_pnl"] = round(m["daily_pnl"], 2)

        total_trading_days = len(days_result)
        if total_trading_days > 0:
            best_day = max(days_result, key=lambda x: x["daily_pnl"])
            worst_day = min(days_result, key=lambda x: x["daily_pnl"])
            win_days = sum(1 for d in days_result if d["daily_pnl"] > 0)
            loss_days = sum(1 for d in days_result if d["daily_pnl"] <= 0)
            avg_daily_pnl = cumulative_pnl / total_trading_days
            avg_daily_pnl_pct = sum(d["daily_pnl_pct"] for d in days_result) / total_trading_days
            
            total_summary = {
                "total_trading_days": total_trading_days,
                "total_cumulative_pnl": round(cumulative_pnl, 2),
                "total_cumulative_pnl_pct": round(sum(d["daily_pnl_pct"] for d in days_result), 2),
                "best_day": {"date": best_day["date"], "pnl": round(best_day["daily_pnl"], 2), "pnl_pct": round(best_day["daily_pnl_pct"], 2)},
                "worst_day": {"date": worst_day["date"], "pnl": round(worst_day["daily_pnl"], 2), "pnl_pct": round(worst_day["daily_pnl_pct"], 2)},
                "win_days": win_days,
                "loss_days": loss_days,
                "avg_daily_pnl": round(avg_daily_pnl, 2),
                "avg_daily_pnl_pct": round(avg_daily_pnl_pct, 2)
            }
        else:
            total_summary = {
                "total_trading_days": 0,
                "total_cumulative_pnl": 0.0,
                "total_cumulative_pnl_pct": 0.0,
                "best_day": None, "worst_day": None,
                "win_days": 0, "loss_days": 0,
                "avg_daily_pnl": 0.0, "avg_daily_pnl_pct": 0.0
            }
        result = {
            "status": "success",
            "daily_budget": self.daily_budget,
            "days": days_result,
            "weekly": list(weekly_data.values()),
            "monthly": list(monthly_data.values()),
            "total_summary": total_summary
        }
        
        # Cache'e kaydet
        try:
            cache_data = result.copy()
            cache_data["_cache_timestamp"] = datetime.now().timestamp()
            with open(self.CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)
        except Exception as e:
            print(f"[BACKTESTER] Cache yazma hatası: {e}")
            
        return result

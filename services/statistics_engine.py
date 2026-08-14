import json
from services.trade_database import get_connection
from services.market_data import MarketDataManager

class StatisticsEngine:
    """
    Teorik Başarı (İstatistik) Motoru:
    - Verilen sinyallerin "maksimum potansiyeli" nedir? (Sermaye bağımsız)
    - O günkü kârlı/tavan oranlarını çıkarır.
    """
    
    @staticmethod
    def evaluate_daily_signals(date_str: str) -> dict:
        signals = MarketDataManager.get_signals(date_str)
        if not signals:
            return {}
            
        total_signals = len(signals)
        hit_ceiling = 0
        hit_plus5 = 0
        total_max_gain = 0.0
        total_close_gain = 0.0
        
        items = []
        for s in signals:
            sym = s['symbol']
            m_price = s['morning_price']
            c_target = s['ceiling_target']
            
            df = MarketDataManager.get_market_data(date_str, sym)
            
            if df.empty or m_price <= 0:
                high_price = m_price
                close_price = m_price
            else:
                high_price = float(df['High'].max())
                close_price = float(df['Close'].iloc[-1])
                
            max_gain = round(((high_price - m_price) / m_price) * 100, 2)
            close_gain = round(((close_price - m_price) / m_price) * 100, 2)
            
            total_max_gain += max_gain
            total_close_gain += close_gain
            
            is_tavan = (high_price >= c_target * 0.995) or (max_gain >= 9.4) or (close_gain >= 9.4)
            is_plus5 = (max_gain >= 5.0) or (close_gain >= 5.0)
            
            if is_tavan:
                hit_ceiling += 1
                badge = "🚀 TAVAN KİLİT"
            elif is_plus5:
                hit_plus5 += 1
                badge = "🎯 +%5 ÜZERİ KÂR"
            elif close_gain > 0:
                badge = "📈 POZİTİF"
            else:
                badge = "🛑 YATAY / DÜZELTME"
                
            items.append({
                "symbol": sym,
                "morning_price": m_price,
                "ceiling_target": c_target,
                "high_price": high_price,
                "close_price": close_price,
                "max_gain_pct": max_gain,
                "close_gain_pct": close_gain,
                "badge": badge
            })
            
        avg_max_gain = round(total_max_gain / total_signals, 2)
        avg_close_gain = round(total_close_gain / total_signals, 2)
        
        return {
            "date": date_str,
            "total_signals": total_signals,
            "hit_ceiling": hit_ceiling,
            "hit_plus5": hit_plus5,
            "avg_max_gain": avg_max_gain,
            "avg_close_gain": avg_close_gain,
            "tavan_rate": round((hit_ceiling / total_signals)*100, 1),
            "plus5_rate": round((hit_plus5 / total_signals)*100, 1),
            "items": items
        }

    @staticmethod
    def get_all_time_kpis() -> dict:
        conn = get_connection()
        cursor = conn.cursor()
        
        # signals tablosundan eşsiz tarihleri bul
        cursor.execute("SELECT DISTINCT date_str FROM signals ORDER BY date_str DESC")
        dates = [r['date_str'] for r in cursor.fetchall()]
        conn.close()
        
        history = []
        for d in dates:
            daily = StatisticsEngine.evaluate_daily_signals(d)
            if daily:
                history.append(daily)
                
        if not history:
            return {"status": "error", "message": "No data"}
            
        total_days = len(history)
        total_cands = sum(h['total_signals'] for h in history)
        t_ceiling = sum(h['hit_ceiling'] for h in history)
        t_plus5 = sum(h['hit_plus5'] for h in history)
        
        c_avg_max = sum(h['avg_max_gain'] for h in history) / total_days if total_days > 0 else 0
        c_avg_close = sum(h['avg_close_gain'] for h in history) / total_days if total_days > 0 else 0
        
        return {
            "status": "success",
            "summary": {
                "total_days_tracked": total_days,
                "total_candidates_tracked": total_cands,
                "total_hit_ceiling": t_ceiling,
                "total_hit_plus5": t_plus5,
                "tavan_success_pct": round((t_ceiling / total_cands) * 100, 1) if total_cands > 0 else 0,
                "plus5_success_pct": round((t_plus5 / total_cands) * 100, 1) if total_cands > 0 else 0,
                "cumulative_avg_max_gain_pct": round(c_avg_max, 2),
                "cumulative_avg_closing_gain_pct": round(c_avg_close, 2),
                "ahlatci_warrant_avg_gain_pct": round(max(0, c_avg_max * 6.2), 2)
            },
            "history": history
        }

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
        hit_positive = 0
        hit_negative = 0
        
        elite_hit_positive = 0
        elite_hit_negative = 0
        elite_total_positive_gain = 0.0
        elite_total_negative_gain = 0.0
        
        total_max_gain = 0.0
        total_close_gain = 0.0
        total_positive_gain = 0.0
        total_negative_gain = 0.0
        
        items = []
        for s in signals:
            sym = s['symbol']
            m_price = float(s['morning_price'] if s['morning_price'] else 0)
            c_target = float(s['ceiling_target'] if s['ceiling_target'] else 0)
            score = float(s['score'] if s['score'] else 0)
            
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
            
            if close_gain > 0:
                hit_positive += 1
                total_positive_gain += close_gain
                if score >= 99.9:
                    elite_hit_positive += 1
                    elite_total_positive_gain += close_gain
            elif close_gain < 0:
                hit_negative += 1
                total_negative_gain += close_gain
                if score >= 99.9:
                    elite_hit_negative += 1
                    elite_total_negative_gain += close_gain
                
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
            "hit_positive": hit_positive,
            "hit_negative": hit_negative,
            "total_positive_gain": round(total_positive_gain, 2),
            "total_negative_gain": round(total_negative_gain, 2),
            "elite_hit_positive": elite_hit_positive,
            "elite_hit_negative": elite_hit_negative,
            "elite_total_positive_gain": round(elite_total_positive_gain, 2),
            "elite_total_negative_gain": round(elite_total_negative_gain, 2),
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
        
        t_positive = sum(h['hit_positive'] for h in history)
        t_negative = sum(h['hit_negative'] for h in history)
        
        sum_pos_gain = sum(h['total_positive_gain'] for h in history)
        sum_neg_gain = sum(h['total_negative_gain'] for h in history)
        
        avg_pos_gain = round(sum_pos_gain / t_positive, 2) if t_positive > 0 else 0
        avg_neg_gain = round(sum_neg_gain / t_negative, 2) if t_negative > 0 else 0
        
        net_pct = round(avg_pos_gain + avg_neg_gain, 2)
        
        # Elite stats
        t_elite_positive = sum(h['elite_hit_positive'] for h in history)
        t_elite_negative = sum(h['elite_hit_negative'] for h in history)
        
        sum_elite_pos_gain = sum(h['elite_total_positive_gain'] for h in history)
        sum_elite_neg_gain = sum(h['elite_total_negative_gain'] for h in history)
        
        avg_elite_pos_gain = round(sum_elite_pos_gain / t_elite_positive, 2) if t_elite_positive > 0 else 0
        avg_elite_neg_gain = round(sum_elite_neg_gain / t_elite_negative, 2) if t_elite_negative > 0 else 0
        
        net_elite_pct = round(avg_elite_pos_gain + avg_elite_neg_gain, 2)
        
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
                "ahlatci_warrant_avg_gain_pct": round(max(0, c_avg_max * 6.2), 2),
                "total_closed_positive": t_positive,
                "total_closed_negative": t_negative,
                "avg_positive_close_gain": avg_pos_gain,
                "avg_negative_close_gain": avg_neg_gain,
                "net_profit_pct": net_pct,
                "elite_closed_positive": t_elite_positive,
                "elite_closed_negative": t_elite_negative,
                "elite_avg_positive_gain": avg_elite_pos_gain,
                "elite_avg_negative_gain": avg_elite_neg_gain,
                "elite_net_profit_pct": net_elite_pct
            },
            "history": history
        }

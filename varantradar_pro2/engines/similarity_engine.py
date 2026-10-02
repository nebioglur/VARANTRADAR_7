import pandas as pd
import numpy as np
from typing import Dict, Any, List

class HistoricalSimilarityEngine:
    """
    Şu anki fiyat/grafik formasyonunu geçmiş yıllardaki hareketlerle kıyaslayarak
    "Tarihsel Benzerlik Skoru" hesaplar ve geçmişteki sonuca göre gelecek projeksiyonu çizer.
    """
    
    @staticmethod
    def find_similar_patterns(df: pd.DataFrame, window_size: int = 20, projection_size: int = 10, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Son 'window_size' (Örn: 20 gün) barlık fiyat hareketine en çok benzeyen 
        geçmiş dönemleri korelasyon ile bulur ve o dönemden sonraki 
        'projection_size' (Örn: 10 gün) içindeki değişimi hesaplar.
        """
        if df.empty or len(df) < (window_size * 2) + projection_size:
            return []
            
        close_prices = df['close'].values
        dates = df.index
        
        # Hedef örüntü (Şu anki son 20 gün)
        current_pattern = close_prices[-window_size:]
        # Normalize et (0-1 arası veya Z-score)
        current_norm = (current_pattern - np.mean(current_pattern)) / (np.std(current_pattern) + 1e-8)
        
        similarities = []
        
        # Geçmişte bu pencereyi kaydır (Son 20 gün + 10 gün projeksiyon payı bırakarak)
        max_idx = len(close_prices) - window_size - projection_size - 1
        
        for i in range(max_idx):
            past_pattern = close_prices[i : i + window_size]
            
            # Düz (flat) veya sıfır varyanslı pencereleri atla
            std = np.std(past_pattern)
            if std < 1e-8:
                continue
                
            past_norm = (past_pattern - np.mean(past_pattern)) / std
            
            # Pearson Korelasyonu
            correlation = np.corrcoef(current_norm, past_norm)[0, 1]
            
            # Sadece pozitif ve yüksek korelasyonları al (Örn: %80 üzeri benzerlik)
            if correlation > 0.80:
                # O dönemden SONRAKİ projection_size (10) gün içindeki değişim
                price_at_match_end = close_prices[i + window_size - 1]
                price_after_proj = close_prices[i + window_size + projection_size - 1]
                
                future_change_pct = ((price_after_proj / price_at_match_end) - 1) * 100
                
                similarities.append({
                    "Date_Start": dates[i].strftime("%Y-%m-%d") if isinstance(dates, pd.DatetimeIndex) else str(i),
                    "Date_End": dates[i + window_size - 1].strftime("%Y-%m-%d") if isinstance(dates, pd.DatetimeIndex) else str(i + window_size - 1),
                    "Similarity_Score": round(correlation * 100, 1),
                    "Future_Change_Pct": round(future_change_pct, 2)
                })
                
        # En yüksek benzerlik skoruna göre sırala
        similarities = sorted(similarities, key=lambda x: x["Similarity_Score"], reverse=True)
        
        # En iyi Top N benzerliği dön (Aynı dönemin çakışmasını engellemek için basit filtre eklenebilir ama şu an basit tutuyoruz)
        filtered_top = []
        seen_dates = set()
        for match in similarities:
            # Sadece yılı / ayı kontrol ederek çok yakın tarihlerin aynı sayılmasını engelleyebiliriz
            year_month = match["Date_Start"][:7] 
            if year_month not in seen_dates:
                filtered_top.append(match)
                seen_dates.add(year_month)
            if len(filtered_top) >= top_n:
                break
                
        return filtered_top

    @staticmethod
    def analyze_similarity(df: pd.DataFrame) -> Dict[str, Any]:
        """Benzerlikleri analiz edip yapay zeka çıkarımı üretir."""
        matches = HistoricalSimilarityEngine.find_similar_patterns(df)
        
        if not matches:
            return {
                "Found": False,
                "Message": "Son 20 günlük fiyat hareketine %80'den fazla benzeyen güçlü bir tarihsel örüntü bulunamadı.",
                "Matches": []
            }
            
        positive_scenarios = sum(1 for m in matches if m["Future_Change_Pct"] > 0)
        total = len(matches)
        
        ai_verdict = "NÖTR"
        if positive_scenarios / total >= 0.66:
            ai_verdict = "YÜKSELİŞ BEKLENTİSİ (Benzer geçmiş dönemlerde hisse çoğunlukla yukarı tepki vermiş)"
        elif positive_scenarios / total <= 0.33:
            ai_verdict = "DÜŞÜŞ BEKLENTİSİ (Benzer geçmiş dönemlerde hisse çoğunlukla satış yemiş)"
            
        avg_change = sum(m["Future_Change_Pct"] for m in matches) / total
            
        return {
            "Found": True,
            "Message": f"Son 20 günlük harekete çok benzeyen {total} geçmiş dönem bulundu.",
            "Matches": matches,
            "AI_Verdict": ai_verdict,
            "Avg_Expected_Change": round(avg_change, 2)
        }

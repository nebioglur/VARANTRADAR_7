import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any

class MarketRegimeEngine:
    """
    V8 Market Regime Engine (Piyasa Rejimi Motoru)
    Belirlediği rejimler:
      - STRONG_BULL: GÜÇLÜ BOĞA (RALLİ)
      - BULL: BOĞA (YÜKSELİŞ TRENDİ)
      - NEUTRAL: NÖTR (YATAY / DENGE)
      - BEAR: AYI (DÜŞÜŞ BASKISI)
      - STRONG_BEAR: GÜÇLÜ AYI (SERT SATIŞ)
      - HIGH_VOLATILITY: YÜKSEK VOLATİLİTE (DALGALI)
    """
    REGIME_TR_MAP = {
        "STRONG_BULL": "GÜÇLÜ BOĞA (RALLİ)",
        "BULL": "BOĞA (YÜKSELİŞ TRENDİ)",
        "NEUTRAL": "NÖTR (YATAY / DENGE)",
        "BEAR": "AYI (DÜŞÜŞ BASKISI)",
        "STRONG_BEAR": "GÜÇLÜ AYI (SERT SATIŞ)",
        "HIGH_VOLATILITY": "YÜKSEK VOLATİLİTE (DALGALI)",
        "DATA_INSUFFICIENT": "VERİ BEKLENİYOR",
        "ERROR": "BİLGİ ALINAMADI"
    }

    def __init__(self):
        self.index_symbol = "XU100.IS"
        
    def determine_regime(self) -> Dict[str, Any]:
        try:
            df = self._fetch_index_df()
            if df is None or df.empty:
                return self._last_known_regime("DATA_INSUFFICIENT")

            # yfinance MultiIndex check
            if hasattr(df.columns, 'nlevels') and df.columns.nlevels > 1:
                df.columns = df.columns.droplevel(1)
                
            close_col = 'close' if 'close' in df.columns else 'Close'
            open_col = 'open' if 'open' in df.columns else 'Open'
            high_col = 'high' if 'high' in df.columns else 'High'
            low_col = 'low' if 'low' in df.columns else 'Low'
            
            close = df[close_col]
            current_price = float(close.iloc[-1])
            prev_price = float(close.iloc[-2]) if len(close) > 1 else current_price
            open_price = float(df[open_col].iloc[-1]) if open_col in df.columns else current_price
            high_price = float(df[high_col].iloc[-1]) if high_col in df.columns else current_price
            low_price = float(df[low_col].iloc[-1]) if low_col in df.columns else current_price
            
            # 1. Canlı BIST Değişimi & Fallback
            # Server yüklüyse canlı hesaplanan değişimi ve piyasa genişliğini al
            live_chg = None
            advancers_ratio = 0.50
            try:
                import sys
                srv = sys.modules.get('server')
                if srv:
                    if hasattr(srv, 'get_xu100_change'):
                        live_chg = srv.get_xu100_change()
                    all_stats = getattr(srv, 'GLOBAL_DASHBOARD_CACHE', {}).get("all_symbols_stats", {})
                    if all_stats and len(all_stats) >= 20:
                        pos = sum(1 for d in all_stats.values() if isinstance(d, dict) and d.get("Change_Pct", 0) > 0)
                        advancers_ratio = pos / len(all_stats)
            except Exception:
                pass
            
            df_change_pct = ((current_price - prev_price) / prev_price) * 100
            if live_chg is not None and abs(live_chg) > 0.05:
                change_pct = float(live_chg)
            else:
                change_pct = float(df_change_pct)

            # 2. EMA Trend Hesaplamaları
            ema5 = close.ewm(span=5, adjust=False).mean()
            ema10 = close.ewm(span=10, adjust=False).mean()
            ema20 = close.ewm(span=20, adjust=False).mean()
            
            c_ema5 = float(ema5.iloc[-1])
            c_ema10 = float(ema10.iloc[-1])
            c_ema20 = float(ema20.iloc[-1])
            
            # 3. Volatilite Analizi (ATR)
            tr1 = df[high_col] - df[low_col]
            tr2 = abs(df[high_col] - close.shift())
            tr3 = abs(df[low_col] - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.rolling(14, min_periods=5).mean()
            if len(atr_14) > 0 and not pd.isna(atr_14.iloc[-1]):
                current_atr = float(atr_14.iloc[-1])
                avg_atr = float(atr_14.mean())
                volatility_state = "HIGH" if current_atr > avg_atr * 1.6 else "NORMAL"
            else:
                volatility_state = "NORMAL"
            

            # 5. DİNAMİK VE ADİL PUANLAMA (0 - 100 Puan)
            # Başlangıç Baseline: 50 (Tam Denge)
            score = 50.0
            
            # A) Günlük Değişim Katkısı (-30 ile +30 arası)
            if change_pct >= 2.5:
                score += 30.0   # Sert Ralli
            elif change_pct >= 1.5:
                score += 22.0   # Belirgin Boğa
            elif change_pct >= 0.6:
                score += 12.0   # Pozitif
            elif change_pct >= 0.0:
                score += 5.0    # Hafif Pozitif
            elif change_pct > -0.6:
                score -= 5.0    # Hafif Negatif
            elif change_pct > -1.5:
                score -= 15.0   # Belirgin Düşüş
            elif change_pct > -2.5:
                score -= 22.0   # Sert Düşüş
            else:
                score -= 30.0   # Ağır Satış / Çöküş

            # B) Piyasa Genişliği Katkısı (-15 ile +15 arası)
            if advancers_ratio >= 0.70:
                score += 15.0   # Piyasanın %70'inden fazlası yeşil
            elif advancers_ratio >= 0.55:
                score += 8.0    # Çoğunluk yeşil
            elif advancers_ratio <= 0.30:
                score -= 15.0   # Çoğunluk kırmızı
            elif advancers_ratio <= 0.45:
                score -= 8.0    # Satıcılar hakim

            # C) Kısa Vade & Orta Vade EMA Konumu
            # Kısa vade momentum (EMA5)
            if current_price > c_ema5:
                score += 8.0
            else:
                score -= 6.0
                
            # Kısa-Orta geçiş (EMA10)
            if current_price > c_ema10:
                score += 6.0
            else:
                score -= 5.0
                
            # Orta vade trend (EMA20)
            if current_price > c_ema20:
                score += 8.0
            else:
                score -= 6.0

            # D) Gün İçi Mum Yapısı (Alıcı / Satıcı Baskısı)
            if current_price > open_price:
                score += 6.0    # Gün içi yeşil gövde
            elif current_price < open_price:
                score -= 6.0    # Gün içi kırmızı gövde

            candle_range = high_price - low_price
            if candle_range > 0:
                close_pos = (current_price - low_price) / candle_range
                if close_pos > 0.75:
                    score += 5.0  # Günün en yükseğine yakın kapanış (Güçlü Boğalar)
                elif close_pos < 0.25:
                    score -= 5.0  # Günün en düşüğüne yakın kapanış (Güçlü Ayılar)

            # Sınırlandırma (0 - 100)
            score = max(5.0, min(95.0, score))
            
            # 6. Rejim Kararı
            regime = "NEUTRAL"
            if score >= 72:
                regime = "STRONG_BULL"
            elif score >= 56:
                regime = "BULL"
            elif score <= 28:
                regime = "STRONG_BEAR"
            elif score <= 42:
                regime = "BEAR"
            else:
                regime = "NEUTRAL"
            
            # Volatilite aşırıysa ve rejim dengedeyse
            if volatility_state == "HIGH" and 35 <= score <= 62:
                regime = "HIGH_VOLATILITY"
                
            regime_label = self.REGIME_TR_MAP.get(regime, regime)
            
            result = {
                "regime": regime_label,
                "regime_code": regime,
                "regime_label": regime_label,
                "score": round(score, 1),
                "xu100_trend": round(change_pct, 2),
                "volatility_state": volatility_state,
                "timestamp": datetime.now().isoformat(),
                "c_ema5": round(c_ema5, 2),
                "c_ema20": round(c_ema20, 2),
                "current_price": round(current_price, 2),
                "advancers_ratio": round(advancers_ratio * 100, 1)
            }
            
            self._save_regime_to_db(result)
            return result
            
        except Exception as e:
            print(f"[V8 Regime Engine] Error: {e}")
            return self._last_known_regime("ERROR")

    def _fetch_index_df(self):
        """XU100 günlük verisini çeker: önce Ticker.history (hızlı), başarısızsa download fallback."""
        try:
            hist = yf.Ticker(self.index_symbol).history(period="2mo", interval="1d")
            if hist is not None and not hist.empty and len(hist) >= 5:
                return hist.copy()
        except Exception:
            pass
        try:
            data = yf.download(self.index_symbol, period="2mo", interval="1d", progress=False)
            if data is not None and not data.empty:
                return data.copy()
        except Exception:
            pass
        return None

    def _last_known_regime(self, status="NEUTRAL"):
        """Yahoo verisi yoksa DB'deki son bilinen rejimi döndürür; yoksa neutral default."""
        try:
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute("SELECT regime, regime_score, xu100_trend, volatility_state, timestamp FROM v8_market_regimes ORDER BY timestamp DESC LIMIT 1")
            row = c.fetchone()
            conn.close()
            if row is not None:
                reg_raw = row["regime"]
                regime_tr = self.REGIME_TR_MAP.get(reg_raw, reg_raw)
                return {
                    "regime": regime_tr,
                    "regime_code": reg_raw,
                    "regime_label": regime_tr,
                    "score": row["regime_score"],
                    "xu100_trend": row["xu100_trend"] or 0.0,
                    "volatility_state": row["volatility_state"] or "NORMAL",
                    "timestamp": row["timestamp"],
                    "stale": True
                }
        except Exception as e:
            print(f"[V8 Regime Engine] Last-known lookup error: {e}")
        return self._default_regime(status)

    def _save_regime_to_db(self, regime_data: dict):
        try:
            from v8_engine.database import V8Database
            conn = V8Database.get_connection()
            c = conn.cursor()
            c.execute('''
                INSERT OR REPLACE INTO v8_market_regimes (timestamp, regime, regime_score, xu100_trend, volatility_state)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                regime_data["timestamp"],
                regime_data.get("regime_code", regime_data["regime"]),
                regime_data["score"],
                regime_data["xu100_trend"],
                regime_data["volatility_state"]
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[V8 Regime Engine] DB Error: {e}")

    def _default_regime(self, status="NEUTRAL"):
        tr_label = self.REGIME_TR_MAP.get(status, "NÖTR (YATAY / DENGE)")
        return {
            "regime": tr_label,
            "regime_code": status,
            "regime_label": tr_label,
            "score": 50.0,
            "xu100_trend": 0.0,
            "volatility_state": "NORMAL",
            "timestamp": datetime.now().isoformat()
        }

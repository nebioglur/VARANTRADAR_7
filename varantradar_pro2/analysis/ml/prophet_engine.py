import pandas as pd
import numpy as np
from typing import Dict, Any, List
import datetime
from sklearn.metrics import r2_score, mean_squared_error

class ProphetProjectionEngine:
    """
    Prophet Tabanlı Fiyat Projeksiyon Motoru (Meta/Facebook AI)
    Zaman serilerindeki trendi ve mevsimselliği (Seasonality) mükemmel yakalar.
    """
    
    def __init__(self):
        # Prophet modelini içe aktar (gecikmeli aktarım, sadece kullanıldığında yüklenmesi için)
        try:
            from prophet import Prophet
            self.Prophet = Prophet
        except ImportError:
            print("[Prophet Engine] Hata: prophet kütüphanesi kurulu değil. 'pip install prophet' çalıştırın.")
            self.Prophet = None

    def generate_projections_real(self, df: pd.DataFrame, steps: int = 5, interval_type: str = '1d', current_price: float = None) -> Dict[str, Any]:
        """
        Geçmiş (Backtest) ve Gelecek (Future) tahminlerini Prophet ile üretir.
        """
        if df.empty or len(df) < steps * 2 or self.Prophet is None:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
            
        df = df.rename(columns=str.lower)
        data = df.dropna().copy()
        
        # Prophet, uzun verilerde mevsimselliği harika öğrenir. 
        # SVR'deki gibi aşırı kırpmaya gerek yok, ancak çok eskiye gitmek de son trendi bozabilir.
        train_size = min(len(data), max(steps * 8, 300))
        data = data.iloc[-train_size:].copy()
        
        # Prophet Formatına Çevir
        data['ds'] = data.index
        # Eğer timezone varsa temizle
        if data['ds'].dt.tz is not None:
            data['ds'] = data['ds'].dt.tz_localize(None)
        
        data['y'] = data['close']
        
        # Sadece ds ve y
        prophet_df = data[['ds', 'y']].copy()
        
        try:
            # Modeli kur
            # Günlük veya haftalık mevsimselliği interval'e göre aç/kapat
            daily_seasonality = True if interval_type == '1h' else False
            weekly_seasonality = True if interval_type in ['1h', '1d'] else False
            yearly_seasonality = True if interval_type in ['1d', '1wk'] else False
            
            m = self.Prophet(daily_seasonality=daily_seasonality, weekly_seasonality=weekly_seasonality, yearly_seasonality=yearly_seasonality)
            m.fit(prophet_df)
            
            # --- BACKTEST TAHMİNİ ---
            # Mevcut tarihleri tahmin ettiriyoruz (Eğitim seti üzeri)
            forecast = m.predict(prophet_df)
            y_train_pred = forecast['yhat'].values
            
            y_real = prophet_df['y'].values
            
            # Anchor (Uyum) Hesaplaması
            shift = 0
            if current_price is not None and len(y_train_pred) > 0:
                shift = current_price - y_train_pred[-1]
                
            backtest_start_idx = max(0, len(y_real) - steps)
            y_backtest_real = y_real[backtest_start_idx:]
            y_backtest_pred_shifted = y_train_pred[backtest_start_idx:] + shift
            
            r2 = r2_score(y_backtest_real, y_backtest_pred_shifted) if len(y_backtest_real) > 1 else 0
            rmse = np.sqrt(mean_squared_error(y_backtest_real, y_backtest_pred_shifted)) if len(y_backtest_real) > 1 else 0
            
            past_real = []
            past_predicted = []
            
            for i in range(backtest_start_idx, len(data)):
                idx_time = prophet_df['ds'].iloc[i]
                
                real_val = round(y_real[i], 2)
                pred_val = round(y_train_pred[i] + shift, 2)
                
                # Etiket formatı
                if interval_type == '1h':
                    label = f"{idx_time.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{idx_time.day} {months[idx_time.month]}"
                    
                obj_real = {"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": real_val, "expected_close": real_val}
                obj_pred = {"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": pred_val, "expected_close": pred_val}
                
                past_real.append(obj_real)
                past_predicted.append(obj_pred)
                
            # --- GELECEK TAHMİNİ ---
            future_dates = m.make_future_dataframe(periods=steps, freq='h' if interval_type == '1h' else ('d' if interval_type == '1d' else 'W'))
            
            # İş günleri / Saatleri Filtresi
            if interval_type == '1d':
                future_dates = future_dates[future_dates['ds'].dt.dayofweek < 5] # Hafta sonunu çıkar
                if len(future_dates) < len(prophet_df) + steps:
                    future_dates = m.make_future_dataframe(periods=steps * 2, freq='d')
                    future_dates = future_dates[future_dates['ds'].dt.dayofweek < 5]
            elif interval_type == '1h':
                future_dates = m.make_future_dataframe(periods=steps * 5, freq='h')
                future_dates = future_dates[
                    (future_dates['ds'].dt.dayofweek < 5) & 
                    (future_dates['ds'].dt.hour >= 10) & 
                    (future_dates['ds'].dt.hour <= 18)
                ]
                    
            # Sadece geleceği almak için
            future_only = future_dates.iloc[len(prophet_df):].head(steps)
            
            future_forecast = m.predict(future_only)
            
            future_predicted = []
            last_close = y_pred_val = current_price if current_price else y_train_pred[-1]
            atr = (data['high'] - data['low']).mean() if 'high' in data.columns else (y_real.max() - y_real.min()) * 0.1
            
            for i in range(len(future_forecast)):
                future_time = future_forecast['ds'].iloc[i]
                y_pred_raw = future_forecast['yhat'].iloc[i]
                y_pred = y_pred_raw + shift
                
                if interval_type == '1h':
                    label = f"{future_time.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{future_time.day} {months[future_time.month]}"
                    
                future_predicted.append({
                    "timestamp": future_time.isoformat(),
                    "time": label if interval_type == '1h' else "",
                    "day": label if interval_type != '1h' else "",
                    "expected": round(y_pred, 2) if interval_type == '1h' else None,
                    "expected_close": round(y_pred, 2) if interval_type != '1h' else None,
                    "expected_open": round(last_close, 2) if interval_type != '1h' else None,
                    "max": round(future_forecast['yhat_upper'].iloc[i] + shift, 2),
                    "min": round(future_forecast['yhat_lower'].iloc[i] + shift, 2)
                })
                last_close = round(y_pred, 2)
                
            return {
                "metrics": {
                    "r2": round(r2 * 100, 2),
                    "rmse": round(rmse, 2)
                },
                "past_real": past_real,
                "past_predicted": past_predicted,
                "future_predicted": future_predicted
            }
            
        except Exception as e:
            print(f"[Prophet Engine] Error: {e}")
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}

    def analyze(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Gerçek verileri çekerek 3 periyotluk tam Prophet projeksiyonu üretir."""
        import yfinance as yf
        
        try:
            df_hourly = yf.Ticker(symbol).history(period="6mo", interval="1h")
        except:
            df_hourly = pd.DataFrame()
            
        try:
            df_daily = yf.Ticker(symbol).history(period="1y", interval="1d")
        except:
            df_daily = pd.DataFrame()
            
        try:
            df_weekly = yf.Ticker(symbol).history(period="5y", interval="1wk")
        except:
            df_weekly = pd.DataFrame()

        return {
            "Intraday_Hourly": self.generate_projections_real(df_hourly, steps=72, interval_type='1h', current_price=current_price),
            "Weekly_Daily": self.generate_projections_real(df_daily, steps=5, interval_type='1d', current_price=current_price),
            "Monthly_Daily": self.generate_projections_real(df_weekly, steps=4, interval_type='1wk', current_price=current_price)
        }

import numpy as np
import pandas as pd
from sklearn.svm import SVR
from sklearn.preprocessing import StandardScaler
from typing import Dict, Any, List

class SVRProjectionEngine:
    """
    CFG-09 Fiyat Projeksiyon Motoru (3D SVR Regression)
    Verilen hisse fiyatı, hacim ve zaman verilerini kullanarak 
    non-lineer Destek Vektör Regresyonu (SVR) ile gelecekteki fiyat adımlarını tahmin eder.
    (Saatlik 10-18 arası, Haftalık ve Aylık tahminler)
    """

    def __init__(self):
        # Zaman serisi trend tahmininde RBF kernel, eğitim veri aralığı dışına (geleceğe) çıkıldığında 
        # ortalamaya (mean) dönme eğilimi gösterir. Bu yüzden saatlik, günlük ve haftalık tahminler 
        # birbirinden bağımsız yönlere sapar.
        # Bunu çözmek ve geleceğe trendi yansıtmak (extrapolate) için Linear kernel kullanıyoruz.
        self.price_scaler = StandardScaler()
        self.feature_scaler = StandardScaler()
        self.model = SVR(kernel='linear', C=10.0, epsilon=0.01)

    def generate_projections_real(self, df: pd.DataFrame, steps: int = 5, interval_type: str = '1d', current_price: float = None) -> Dict[str, Any]:
        """
        Gerçek makine öğrenimi ile belirtilen veri seti üzerinden 'steps' adım sonrasını tahmin eder.
        Ayrıca geçmiş 'steps' adım için (Backtest) gerçek ve tahmin edilen değerleri döndürür.
        """
        if df.empty or len(df) < steps * 2:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}

        df = df.rename(columns=str.lower)
        data = df.dropna().copy()
        
        # Modeli daha hassas ve güncel trende odaklamak için tüm veriyi değil, 
        # sadece tahmin edilecek adımın (steps) 4-5 katı kadar geçmiş veriyi alıyoruz.
        # Böylece Linear model, 6 aylık dümdüz bir çizgi yerine son dönemin trendini çizer.
        train_size = min(len(data), max(steps * 4, 100))
        data = data.iloc[-train_size:]
            
        X = np.arange(len(data)).reshape(-1, 1)
        if 'volume' in data.columns and data['volume'].sum() > 0:
            volume_data = data['volume'].values.reshape(-1, 1)
            X_multi = np.hstack((X, volume_data))
        else:
            momentum = data['close'].diff().fillna(0).values.reshape(-1, 1)
            X_multi = np.hstack((X, momentum))
            
        y = data['close'].values.reshape(-1, 1)
        
        try:
            from sklearn.metrics import r2_score, mean_squared_error
            X_scaled = self.feature_scaler.fit_transform(X_multi)
            y_scaled = self.price_scaler.fit_transform(y).ravel()
            
            self.model.fit(X_scaled, y_scaled)
            
            # Tüm eğitim seti üzerinde tahmin
            y_train_pred_scaled = self.model.predict(X_scaled)
            y_train_pred = self.price_scaler.inverse_transform(y_train_pred_scaled.reshape(-1, 1)).ravel()
            
            # Coherence (Uyum) için sapma hesabı
            shift = 0
            if current_price is not None and len(y_train_pred) > 0:
                shift = current_price - y_train_pred[-1]
                
            # --- BACKTEST PENCERESİ (Son 'steps' kadar) ---
            # Kullanıcının tam istediği gibi R2 ve RMSE SADECE bu geçmiş pencerede ve 
            # kaydırılmış (anchorlanmış) son veriler üzerinde hesaplanacak.
            backtest_start_idx = max(0, len(y) - steps)
            y_backtest_real = y[backtest_start_idx:].ravel()
            y_backtest_pred_shifted = y_train_pred[backtest_start_idx:] + shift
            
            r2 = r2_score(y_backtest_real, y_backtest_pred_shifted) if len(y_backtest_real) > 1 else 0
            rmse = np.sqrt(mean_squared_error(y_backtest_real, y_backtest_pred_shifted)) if len(y_backtest_real) > 1 else 0
            
            import datetime
            past_real = []
            past_predicted = []
            future_predicted = []
            
            # Geçmiş (Backtest) verilerini listelere ekle
            for i in range(backtest_start_idx, len(data)):
                idx_time = data.index[i]
                if isinstance(idx_time, str): idx_time = pd.to_datetime(idx_time)
                
                real_val = round(y[i][0], 2)
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
            
            # --- GELECEK TAHMİNİ (Future Projections) ---
            last_index = len(data)
            last_volume = data['volume'].iloc[-1] if 'volume' in data.columns else 0
            last_close = data['close'].iloc[-1]
            atr = (data['high'] - data['low']).mean()
            
            current_time = data.index[-1]
            if isinstance(current_time, str):
                current_time = pd.to_datetime(current_time)
                
            for i in range(1, steps + 1):
                if interval_type == '1h':
                    current_time += datetime.timedelta(hours=1)
                    if current_time.hour > 18 or (current_time.hour == 18 and current_time.minute > 10):
                        current_time += datetime.timedelta(days=1)
                        current_time = current_time.replace(hour=10, minute=0)
                    while current_time.weekday() >= 5:
                        current_time += datetime.timedelta(days=1)
                elif interval_type == '1wk':
                    current_time += datetime.timedelta(weeks=1)
                else:
                    current_time += datetime.timedelta(days=1)
                    while current_time.weekday() >= 5:
                        current_time += datetime.timedelta(days=1)
                
                pred_vol = last_volume * (1 + np.random.uniform(-0.05, 0.05))
                X_pred = np.array([[last_index + i, pred_vol]])
                X_pred_scaled = self.feature_scaler.transform(X_pred)
                
                y_pred_scaled = self.model.predict(X_pred_scaled)
                y_pred_raw = self.price_scaler.inverse_transform(y_pred_scaled.reshape(-1, 1))[0][0]
                y_pred = y_pred_raw + shift
                
                if interval_type == '1h':
                    label = f"{current_time.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{current_time.day} {months[current_time.month]}"
                
                future_predicted.append({
                    "timestamp": current_time.isoformat(),
                    "time": label if interval_type == '1h' else "",
                    "day": label if interval_type != '1h' else "",
                    "expected": round(y_pred, 2) if interval_type == '1h' else None,
                    "expected_close": round(y_pred, 2) if interval_type != '1h' else None,
                    "expected_open": round(last_close, 2) if interval_type != '1h' else None,
                    "max": round(y_pred + atr, 2),
                    "min": round(y_pred - atr, 2)
                })
                last_close = y_pred
                last_volume = pred_vol
                
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
            print(f"[SVR Engine] Error: {e}")
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}

    def generate_intraday_projections(self, df: pd.DataFrame, current_price: float) -> List[Dict[str, Any]]:
        # Bu metod arayüz uyumluluğu için tutuluyor, ancak artık gerçek model kullanıyor
        return self.generate_projections_real(df, steps=72, interval_type='1h')

    def generate_daily_projections(self, df: pd.DataFrame, days: int = 5) -> List[Dict[str, Any]]:
        # Arayüz uyumluluğu için
        return self.generate_projections_real(df, steps=days, interval_type='1d')

    def analyze(self, symbol: str, current_price: float) -> Dict[str, Any]:
        """Gerçek verileri çekerek 3 periyotluk tam SVR projeksiyonu üretir."""
        import yfinance as yf
        
        # 1. Saatlik Veri (6 Ay = ~130 gün) yfinance'de 1h maks 730 gün
        try:
            df_hourly = yf.Ticker(symbol).history(period="6mo", interval="1h")
        except Exception:
            df_hourly = pd.DataFrame()
            
        # 2. Günlük Veri (1 Yıl)
        try:
            df_daily = yf.Ticker(symbol).history(period="1y", interval="1d")
        except Exception:
            df_daily = pd.DataFrame()
            
        # 3. Haftalık Veri (5 Yıl)
        try:
            df_weekly = yf.Ticker(symbol).history(period="5y", interval="1wk")
        except Exception:
            df_weekly = pd.DataFrame()

        return {
            "Intraday_Hourly": self.generate_projections_real(df_hourly, steps=72, interval_type='1h', current_price=current_price),
            "Weekly_Daily": self.generate_projections_real(df_daily, steps=5, interval_type='1d', current_price=current_price),
            "Monthly_Daily": self.generate_projections_real(df_weekly, steps=4, interval_type='1wk', current_price=current_price)
        }

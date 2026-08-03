import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.metrics import r2_score, mean_squared_error

class XGBoostProjectionEngine:
    def __init__(self):
        try:
            import xgboost as xgb
            self.xgb = xgb
        except ImportError:
            print("[XGBoost Engine] Hata: xgboost kurulu değil.")
            self.xgb = None

    def _create_features(self, df: pd.DataFrame, lags: int = 5):
        df_feat = df.copy()
        for i in range(1, lags + 1):
            df_feat[f'lag_{i}'] = df_feat['close'].shift(i)
            if 'volume' in df_feat.columns:
                df_feat[f'vol_lag_{i}'] = df_feat['volume'].shift(i)
        
        df_feat['momentum_1'] = df_feat['close'].diff(1)
        df_feat['momentum_3'] = df_feat['close'].diff(3)
        
        return df_feat

    def generate_projections_real(self, df: pd.DataFrame, steps: int = 5, interval_type: str = '1d', current_price: float = None) -> Dict[str, Any]:
        if df.empty or len(df) < steps * 2 or self.xgb is None:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
            
        df = df.rename(columns=str.lower)
        data = df.dropna().copy()
        
        train_size = min(len(data), max(steps * 10, 500))
        data = data.iloc[-train_size:].copy()
        
        lags = 5
        data_feat = self._create_features(data, lags=lags).dropna()
        
        if len(data_feat) < steps:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
            
        data_feat['target'] = data_feat['close'].shift(-1)
        
        train_data = data_feat.dropna(subset=['target']).copy()
        
        feature_cols = [c for c in data_feat.columns if c not in ['close', 'target', 'open', 'high', 'low', 'volume', 'ds', 'y']]
        
        X_train = train_data[feature_cols]
        y_train = train_data['target']
        
        try:
            model = self.xgb.XGBRegressor(n_estimators=100, learning_rate=0.05, max_depth=3, objective='reg:squarederror')
            model.fit(X_train, y_train)
            
            y_train_pred = model.predict(X_train)
            
            shift = 0
            if current_price is not None and len(y_train_pred) > 0:
                shift = current_price - y_train_pred[-1]
                
            backtest_start_idx = max(0, len(y_train_pred) - steps)
            y_backtest_real = train_data['target'].values[backtest_start_idx:]
            y_backtest_pred_shifted = y_train_pred[backtest_start_idx:] + shift
            
            r2 = r2_score(y_backtest_real, y_backtest_pred_shifted) if len(y_backtest_real) > 1 else 0
            rmse = np.sqrt(mean_squared_error(y_backtest_real, y_backtest_pred_shifted)) if len(y_backtest_real) > 1 else 0
            
            past_real = []
            past_predicted = []
            
            for i in range(backtest_start_idx, len(train_data)):
                idx_time = train_data.index[i]
                
                real_val = round(train_data['target'].iloc[i], 2)
                pred_val = round(y_train_pred[i] + shift, 2)
                
                if interval_type == '1h':
                    label = f"{idx_time.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{idx_time.day} {months[idx_time.month]}"
                    
                obj_real = {"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": real_val, "expected_close": real_val}
                obj_pred = {"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": pred_val, "expected_close": pred_val}
                
                past_real.append(obj_real)
                past_predicted.append(obj_pred)
                
            future_predicted = []
            last_row = data_feat.iloc[-1:].copy()
            current_dt = last_row.index[0]
            
            last_close = current_price if current_price else y_train_pred[-1]
            
            for step in range(steps):
                X_future = last_row[feature_cols]
                next_pred = model.predict(X_future)[0]
                next_pred_shifted = next_pred + shift
                
                if interval_type == '1h':
                    current_dt = current_dt + pd.Timedelta(hours=1)
                    if current_dt.hour > 18 or (current_dt.hour == 18 and current_dt.minute > 10):
                        current_dt = current_dt + pd.Timedelta(days=1)
                        current_dt = current_dt.replace(hour=10, minute=0)
                    while current_dt.dayofweek >= 5: 
                        current_dt = current_dt + pd.Timedelta(days=1)
                elif interval_type == '1d':
                    current_dt = current_dt + pd.Timedelta(days=1)
                    while current_dt.dayofweek >= 5: 
                        current_dt = current_dt + pd.Timedelta(days=1)
                else:
                    current_dt = current_dt + pd.Timedelta(weeks=1)
                    
                if interval_type == '1h':
                    label = f"{current_dt.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{current_dt.day} {months[current_dt.month]}"
                    
                future_predicted.append({
                    "timestamp": current_dt.isoformat(),
                    "time": label if interval_type == '1h' else "",
                    "day": label if interval_type != '1h' else "",
                    "expected": round(next_pred_shifted, 2) if interval_type == '1h' else None,
                    "expected_close": round(next_pred_shifted, 2) if interval_type != '1h' else None,
                    "expected_open": round(last_close, 2) if interval_type != '1h' else None,
                    "max": round(next_pred_shifted * 1.01, 2),
                    "min": round(next_pred_shifted * 0.99, 2)
                })
                
                last_close = round(next_pred_shifted, 2)
                
                new_row = last_row.copy()
                for i in range(lags, 1, -1):
                    new_row[f'lag_{i}'] = new_row[f'lag_{i-1}']
                new_row['lag_1'] = next_pred
                
                new_row['momentum_1'] = next_pred - last_row['lag_1'].values[0]
                new_row['momentum_3'] = next_pred - last_row['lag_3'].values[0] if lags >=3 else new_row['momentum_1']
                
                last_row = new_row
                
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
            print(f"[XGBoost Engine] Error: {e}")
            import traceback
            traceback.print_exc()
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}

    def analyze(self, symbol: str, current_price: float) -> Dict[str, Any]:
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

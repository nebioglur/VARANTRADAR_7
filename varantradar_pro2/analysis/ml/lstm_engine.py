import pandas as pd
import numpy as np
from typing import Dict, Any
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from sklearn.neural_network import MLPRegressor
import os

class LSTMProjectionEngine:
    def __init__(self):
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        try:
            import tensorflow as tf
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            self.tf = tf
            self.Sequential = Sequential
            self.LSTM = LSTM
            self.Dense = Dense
            self.Dropout = Dropout
        except ImportError:
            print("[LSTM Engine] Hata: tensorflow kurulu değil. MLPRegressor kullanılacak.")
            self.tf = None

    def _create_dataset(self, data: np.ndarray, time_step: int = 5):
        X, Y = [], []
        for i in range(len(data) - time_step):
            X.append(data[i:(i + time_step), :])
            Y.append(data[i + time_step, 0])
        return np.array(X), np.array(Y)

    def generate_projections_real(self, df: pd.DataFrame, steps: int = 5, interval_type: str = '1d', current_price: float = None) -> Dict[str, Any]:
        if df.empty or len(df) < steps * 3:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
            
        df = df.rename(columns=str.lower)
        data = df.dropna().copy()
        
        train_size = min(len(data), max(steps * 20, 1000))
        data = data.iloc[-train_size:].copy()
        
        features = ['close']
        if 'volume' in data.columns:
            features.append('volume')
            
        dataset = data[features].values
        
        scaler = MinMaxScaler(feature_range=(0, 1))
        scaled_data = scaler.fit_transform(dataset)
        
        close_scaler = MinMaxScaler(feature_range=(0, 1))
        close_scaler.fit(dataset[:, 0].reshape(-1, 1))
        
        time_step = max(5, steps)
        if len(scaled_data) <= time_step * 2:
             return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
             
        X, y = self._create_dataset(scaled_data, time_step)
        
        if len(X) == 0:
            return {"metrics": {"r2": 0, "rmse": 0}, "past_real": [], "past_predicted": [], "future_predicted": []}
            
        try:
            if self.tf is not None:
                model = self.Sequential()
                model.add(self.LSTM(50, return_sequences=True, input_shape=(time_step, len(features))))
                model.add(self.Dropout(0.1))
                model.add(self.LSTM(50, return_sequences=False))
                model.add(self.Dense(25))
                model.add(self.Dense(1))
                
                model.compile(optimizer='adam', loss='mean_squared_error')
                model.fit(X, y, batch_size=16, epochs=10, verbose=0)
                
                train_predict = model.predict(X, verbose=0)
            else:
                # MLPRegressor Fallback
                X_2d = X.reshape(X.shape[0], X.shape[1] * X.shape[2])
                model = MLPRegressor(hidden_layer_sizes=(50, 25), max_iter=200, random_state=42)
                model.fit(X_2d, y)
                train_predict = model.predict(X_2d).reshape(-1, 1)
            
            train_predict_unscaled = close_scaler.inverse_transform(train_predict).flatten()
            y_unscaled = close_scaler.inverse_transform(y.reshape(-1, 1)).flatten()
            
            shift = 0
            if current_price is not None and len(train_predict_unscaled) > 0:
                shift = current_price - train_predict_unscaled[-1]
                
            backtest_start_idx = max(0, len(train_predict_unscaled) - steps)
            y_backtest_real = y_unscaled[backtest_start_idx:]
            y_backtest_pred_shifted = train_predict_unscaled[backtest_start_idx:] + shift
            
            r2 = r2_score(y_backtest_real, y_backtest_pred_shifted) if len(y_backtest_real) > 1 else 0
            rmse = np.sqrt(mean_squared_error(y_backtest_real, y_backtest_pred_shifted)) if len(y_backtest_real) > 1 else 0
            
            past_real = []
            past_predicted = []
            
            start_idx = time_step + backtest_start_idx
            
            for i in range(len(y_backtest_real)):
                original_idx = start_idx + i
                if original_idx >= len(data): break
                idx_time = data.index[original_idx]
                
                real_val = round(y_backtest_real[i], 2)
                pred_val = round(y_backtest_pred_shifted[i], 2)
                
                if interval_type == '1h':
                    label = f"{idx_time.strftime('%H:%M')}"
                else:
                    months = ["", "Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
                    label = f"{idx_time.day} {months[idx_time.month]}"
                    
                past_real.append({"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": real_val, "expected_close": real_val})
                past_predicted.append({"timestamp": idx_time.isoformat(), "time": label if interval_type=='1h' else "", "day": label if interval_type!='1h' else "", "expected": pred_val, "expected_close": pred_val})
                
            future_predicted = []
            
            last_window = scaled_data[-time_step:]
            curr_input = last_window.reshape(1, time_step, len(features))
            
            current_dt = data.index[-1]
            last_close = current_price if current_price else train_predict_unscaled[-1]
            
            for step in range(steps):
                if self.tf is not None:
                    next_pred_scaled = model.predict(curr_input, verbose=0)[0][0]
                else:
                    curr_input_2d = curr_input.reshape(1, time_step * len(features))
                    next_pred_scaled = model.predict(curr_input_2d)[0]
                    
                next_pred_unscaled = close_scaler.inverse_transform([[next_pred_scaled]])[0][0]
                
                next_pred_shifted = next_pred_unscaled + shift
                
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
                
                new_feature_vector = np.zeros((1, len(features)))
                new_feature_vector[0, 0] = next_pred_scaled
                if len(features) > 1:
                    new_feature_vector[0, 1] = curr_input[0, -1, 1] 
                    
                curr_input = np.append(curr_input[:, 1:, :], [new_feature_vector], axis=1)
                
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
            print(f"[LSTM Engine] Error: {e}")
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

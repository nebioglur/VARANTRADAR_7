import pandas as pd
import numpy as np

class BacktestEngine:
    """
    VarantRadar Pro V6 - Backtest Motoru
    Tarihsel veriler üzerinde kural tabanlı stratejileri test eder ve finansal metrikleri hesaplar.
    """
    def __init__(self, initial_capital: float = 100000.0, commission_pct: float = 0.002, slippage_pct: float = 0.001):
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        
    def run_backtest(self, df: pd.DataFrame, strategy_name: str = "MACD_RSI_CROSS") -> dict:
        """
        Geçmiş veri üzerinde simülasyon çalıştırır (Modül 1, 2).
        Parametreler vectorize mantığıyla hızlıca hesaplanır.
        """
        if df.empty or len(df) < 50:
            return {"error": "Veri yetersiz"}
            
        # Copy df to avoid setting with copy warnings
        data = df.copy()
        
        # Sinyal Üretimi
        data['Signal'] = 0
        if strategy_name == "MACD_RSI_CROSS":
            # AL Sinyali: MACD > Signal ve RSI < 70 ve EMA(20) > EMA(50)
            data.loc[(data['macd'] > data['macd_signal']) & (data['rsi'] < 70) & (data['ema'] > data['sma']), 'Signal'] = 1
            # SAT Sinyali: MACD < Signal ve RSI > 30
            data.loc[(data['macd'] < data['macd_signal']) & (data['rsi'] > 30), 'Signal'] = -1
        elif strategy_name == "RSI_MEAN_REVERSION":
            data.loc[data['rsi'] < 30, 'Signal'] = 1
            data.loc[data['rsi'] > 70, 'Signal'] = -1
        else:
            # Sadece elde tut (Buy and Hold benchmark)
            data['Signal'] = 1

        # İşlem Simülasyonu
        position = 0 # 1=Long, 0=Flat
        entry_price = 0.0
        trades = []
        
        for index, row in data.iterrows():
            if row['Signal'] == 1 and position == 0:
                # AL
                entry_price = row['close'] * (1 + self.slippage_pct)
                position = 1
                entry_date = row['date']
            elif row['Signal'] == -1 and position == 1:
                # SAT
                exit_price = row['close'] * (1 - self.slippage_pct)
                
                # Komisyon Hesabı
                cost = (entry_price * self.commission_pct) + (exit_price * self.commission_pct)
                pnl = (exit_price - entry_price) - cost
                pnl_pct = (pnl / entry_price) * 100
                
                trades.append({
                    "entry_date": entry_date,
                    "exit_date": row['date'],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "duration": (row['date'] - entry_date).days if isinstance(row['date'], pd.Timestamp) else 0
                })
                position = 0

        # Açık kalan pozisyonu güncel fiyatla kapat (Mark-to-market)
        if position == 1:
            exit_price = data['close'].iloc[-1] * (1 - self.slippage_pct)
            cost = (entry_price * self.commission_pct) + (exit_price * self.commission_pct)
            pnl = (exit_price - entry_price) - cost
            trades.append({
                "entry_date": entry_date,
                "exit_date": data['date'].iloc[-1],
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "pnl_pct": (pnl / entry_price) * 100,
                "duration": 0
            })

        # Performans Metrikleri Hesaplama (Modül 5)
        return self._calculate_metrics(trades)

    def _calculate_metrics(self, trades: list) -> dict:
        if not trades:
            return {"error": "Hiç işlem yapılmadı."}
            
        df_trades = pd.DataFrame(trades)
        total_trades = len(df_trades)
        winning_trades = df_trades[df_trades['pnl'] > 0]
        losing_trades = df_trades[df_trades['pnl'] <= 0]
        
        win_rate = len(winning_trades) / total_trades * 100
        
        avg_win = winning_trades['pnl_pct'].mean() if not winning_trades.empty else 0
        avg_loss = losing_trades['pnl_pct'].mean() if not losing_trades.empty else 0
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Cumulative Equity & Max Drawdown
        df_trades['cumulative_pnl'] = df_trades['pnl'].cumsum()
        df_trades['equity'] = self.initial_capital + df_trades['cumulative_pnl']
        df_trades['peak'] = df_trades['equity'].cummax()
        df_trades['drawdown'] = (df_trades['equity'] - df_trades['peak']) / df_trades['peak'] * 100
        max_drawdown = df_trades['drawdown'].min()
        
        # Sortino Ratio (Basitleştirilmiş)
        returns = df_trades['pnl_pct'] / 100
        downside_returns = returns[returns < 0]
        sortino = (returns.mean() / downside_returns.std() * np.sqrt(252)) if not downside_returns.empty and downside_returns.std() > 0 else 0
        
        total_pnl = df_trades['pnl'].sum()
        total_return_pct = (total_pnl / self.initial_capital) * 100
        
        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 2),
            "total_return_pct": round(total_return_pct, 2),
            "max_drawdown": round(abs(max_drawdown), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(abs(avg_loss), 2),
            "risk_reward": round(risk_reward, 2),
            "sortino_ratio": round(sortino, 2),
            "trades": trades
        }

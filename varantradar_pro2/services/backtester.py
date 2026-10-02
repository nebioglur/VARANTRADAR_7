import pandas as pd
from utils.logger import logger

class BacktestEngine:
    def __init__(self, initial_capital: float = 10000.0):
        self.initial_capital = initial_capital

    def run_backtest(self, df: pd.DataFrame, signals_column: str = 'Action') -> dict:
        """
        Runs a simplified backtest on a dataframe containing Buy/Sell signals.
        Assume 'Action' column has 'AL', 'SAT', or 'BEKLE'.
        """
        if df.empty or signals_column not in df.columns:
            logger.warning("Backtest failed: No data or signals column missing.")
            return {}

        capital = self.initial_capital
        position_shares = 0
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        peak_capital = capital
        max_drawdown = 0.0

        trade_history = []

        for index, row in df.iterrows():
            price = row['close']
            signal = row[signals_column]

            if signal == 'AL' and position_shares == 0:
                # Buy as many shares as possible
                position_shares = int(capital / price)
                capital -= position_shares * price
                trade_history.append({"type": "BUY", "price": price, "date": index})

            elif signal == 'SAT' and position_shares > 0:
                # Sell all shares
                revenue = position_shares * price
                capital += revenue
                
                # Check trade outcome
                buy_price = trade_history[-1]['price']
                if price > buy_price:
                    winning_trades += 1
                else:
                    losing_trades += 1
                    
                total_trades += 1
                trade_history.append({"type": "SELL", "price": price, "date": index})
                position_shares = 0

            # Calculate Drawdown
            current_portfolio_value = capital + (position_shares * price)
            if current_portfolio_value > peak_capital:
                peak_capital = current_portfolio_value
            
            drawdown = (peak_capital - current_portfolio_value) / peak_capital * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Final close out if still holding
        if position_shares > 0:
            final_price = df['close'].iloc[-1]
            capital += position_shares * final_price
            if final_price > trade_history[-1]['price']:
                winning_trades += 1
            else:
                losing_trades += 1
            total_trades += 1

        final_return_pct = ((capital - self.initial_capital) / self.initial_capital) * 100
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        result = {
            "initial_capital": self.initial_capital,
            "final_capital": round(capital, 2),
            "return_pct": round(final_return_pct, 2),
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades
        }

        logger.info(f"Backtest Result: Return: {result['return_pct']}%, Win Rate: {result['win_rate_pct']}%, Max DD: {result['max_drawdown_pct']}%")
        return result

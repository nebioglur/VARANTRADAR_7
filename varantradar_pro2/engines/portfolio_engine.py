import pandas as pd
import numpy as np
from datetime import datetime
from database.db_manager import DBManager
from utils.logger import logger

class PortfolioEngine:
    """
    VarantRadar Pro V5 - Profesyonel Portföy ve İşlem Yöneticisi
    Kağıt üstünde (Paper Trading) portföy ve pozisyon yönetimini DB üzerinden sağlar.
    """
    def __init__(self):
        self.db = DBManager()
        self.max_portfolio_risk_pct = 0.10 # Max %10 of total capital tied up in a single trade
        self.max_trade_risk_pct = 0.02    # Max %2 of total capital can be lost in a single trade

    def get_portfolio_summary(self) -> dict:
        """Returns the current portfolio balance and PnL."""
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM portfolio ORDER BY id DESC LIMIT 1", conn)
            if not df.empty:
                return df.iloc[0].to_dict()
            return {"total_capital": 0, "available_balance": 0, "used_margin": 0, "total_pnl": 0}
        finally:
            conn.close()

    def get_institutional_metrics(self) -> dict:
        """Modül 6: Kurumsal Risk (VaR, Sharpe, Max Drawdown)"""
        trades = self.get_trade_history()
        if trades.empty or len(trades) < 5:
            return {"VaR_95": 0, "Sharpe": 0, "Max_Drawdown": 0, "Note": "Yeterli işlem geçmişi yok."}
            
        # PnL percentages
        trades['pnl_pct'] = trades['realized_pnl'] / (trades['entry_price'] * trades['quantity'])
        
        # Sharpe Ratio (Basit simülasyon: Mean / StdDev * sqrt(252))
        mean_pnl = trades['pnl_pct'].mean()
        std_pnl = trades['pnl_pct'].std()
        sharpe = (mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0
        
        # Value at Risk (VaR) %95 Confidence (Tarihsel)
        var_95 = np.percentile(trades['pnl_pct'], 5) * 100 # Yüzde olarak
        
        # Max Drawdown
        cumulative_returns = (1 + trades['pnl_pct']).cumprod()
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdown = (cumulative_returns - running_max) / running_max
        max_dd = drawdown.min() * 100
        
        return {
            "VaR_95": round(var_95, 2),
            "Sharpe": round(sharpe, 2),
            "Max_Drawdown": round(max_dd, 2),
            "Note": "Kurumsal metrikler hesaplandı."
        }

    def get_active_positions(self) -> pd.DataFrame:
        """Returns all open positions."""
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM active_positions", conn)
            return df
        finally:
            conn.close()

    def get_trade_history(self) -> pd.DataFrame:
        """Returns all closed trades."""
        conn = self.db.get_connection()
        try:
            df = pd.read_sql_query("SELECT * FROM trade_journal ORDER BY closed_at DESC", conn)
            return df
        finally:
            conn.close()

    def calculate_position_size(self, current_price: float, stop_loss: float) -> dict:
        """
        Calculates position size strictly adhering to V5 Risk Rules.
        """
        portfolio = self.get_portfolio_summary()
        total_capital = portfolio.get('total_capital', 100000.0)
        available_cash = portfolio.get('available_balance', 100000.0)
        
        # Risk amount based on 2% of total capital
        max_risk_amount = total_capital * self.max_trade_risk_pct
        risk_per_unit = abs(current_price - stop_loss)
        
        if risk_per_unit <= 0:
            return {"units": 0, "investment": 0, "risk_amount": 0, "note": "Geçersiz Stop Loss"}
            
        units_by_risk = int(max_risk_amount / risk_per_unit)
        
        # Max capital to tie up is 10% of total capital
        max_investment_allowed = total_capital * self.max_portfolio_risk_pct
        units_by_capital = int(max_investment_allowed / current_price)
        
        # The recommended units is the minimum of the two constraints
        recommended_units = min(units_by_risk, units_by_capital)
        total_investment = recommended_units * current_price
        
        # Cannot exceed available cash
        if total_investment > available_cash:
            recommended_units = int(available_cash / current_price)
            total_investment = recommended_units * current_price
            
        return {
            "units": recommended_units,
            "investment": round(total_investment, 2),
            "risk_amount": round(recommended_units * risk_per_unit, 2),
            "note": "Risk/Sermaye kurallarına uygun hesaplandı."
        }

    def execute_trade(self, symbol: str, asset_type: str, direction: str, quantity: int, price: float, stop_loss: float, take_profit: float, strategy_note: str = "") -> dict:
        """
        Executes a Buy (Long) or Sell (Short) order and updates Portfolio & Positions.
        """
        if quantity <= 0:
            return {"success": False, "message": "Geçersiz miktar."}
            
        total_cost = quantity * price
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # 1. Check Balance for new Long/Short entries
            cursor.execute("SELECT * FROM portfolio ORDER BY id DESC LIMIT 1")
            portfolio = cursor.fetchone()
            if not portfolio:
                return {"success": False, "message": "Portföy bulunamadı."}
                
            avail_balance = portfolio[2]
            
            # Simplified logic: Opening a new position deducts from avail_balance
            # If position exists, average the cost (Not fully implemented here, keeping it simple: separate entries or block)
            cursor.execute("SELECT id, quantity, average_cost FROM active_positions WHERE symbol=? AND direction=?", (symbol, direction))
            existing_pos = cursor.fetchone()
            
            # Log Order
            now = datetime.now().isoformat()
            cursor.execute('''INSERT INTO order_history (symbol, order_type, action, quantity, price, status, created_at, executed_at) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (symbol, 'MARKET', 'BUY' if direction=='LONG' else 'SELL', quantity, price, 'FILLED', now, now))
            
            if existing_pos:
                # Average Down/Up
                old_qty = existing_pos[1]
                old_avg = existing_pos[2]
                new_qty = old_qty + quantity
                new_avg = ((old_qty * old_avg) + (quantity * price)) / new_qty
                
                cursor.execute('''UPDATE active_positions 
                                  SET quantity=?, average_cost=?, stop_loss=?, take_profit=?, last_updated=? 
                                  WHERE id=?''', 
                               (new_qty, new_avg, stop_loss, take_profit, now, existing_pos[0]))
            else:
                # New Position
                if total_cost > avail_balance:
                    return {"success": False, "message": "Yetersiz Bakiye."}
                    
                cursor.execute('''INSERT INTO active_positions (symbol, asset_type, direction, quantity, average_cost, current_price, stop_loss, take_profit, opened_at, last_updated)
                                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                               (symbol, asset_type, direction, quantity, price, price, stop_loss, take_profit, now, now))
                
            # Deduct Balance
            new_avail = avail_balance - total_cost
            used_margin = portfolio[3] + total_cost
            cursor.execute("UPDATE portfolio SET available_balance=?, used_margin=?, last_updated=? WHERE id=?", 
                           (new_avail, used_margin, now, portfolio[0]))
                           
            conn.commit()
            return {"success": True, "message": f"{symbol} için {quantity} adet {direction} pozisyon açıldı."}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Trade Error: {e}")
            return {"success": False, "message": str(e)}
        finally:
            conn.close()

    def close_position(self, symbol: str, exit_price: float, strategy_note: str = "") -> dict:
        """
        Closes an active position, calculates Realized PnL, updates Portfolio and Trade Journal.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM active_positions WHERE symbol=?", (symbol,))
            pos = cursor.fetchone()
            if not pos:
                return {"success": False, "message": "Aktif pozisyon bulunamadı."}
                
            pos_id, sym, asset_type, direction, qty, avg_cost, _, _, _, _, opened_at, _ = pos
            now = datetime.now().isoformat()
            
            # Calculate PnL
            if direction == 'LONG':
                realized_pnl = (exit_price - avg_cost) * qty
                pnl_pct = ((exit_price - avg_cost) / avg_cost) * 100
            else:
                realized_pnl = (avg_cost - exit_price) * qty
                pnl_pct = ((avg_cost - exit_price) / avg_cost) * 100
                
            # Log Order
            cursor.execute('''INSERT INTO order_history (symbol, order_type, action, quantity, price, status, created_at, executed_at) 
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                           (symbol, 'MARKET', 'SELL' if direction=='LONG' else 'BUY', qty, exit_price, 'FILLED', now, now))
            
            # Write to Journal
            cursor.execute('''INSERT INTO trade_journal (symbol, direction, quantity, entry_price, exit_price, realized_pnl, pnl_percentage, strategy_note, closed_at)
                              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (symbol, direction, qty, avg_cost, exit_price, realized_pnl, pnl_pct, strategy_note, now))
                           
            # Delete Position
            cursor.execute("DELETE FROM active_positions WHERE id=?", (pos_id,))
            
            # Update Portfolio
            cursor.execute("SELECT * FROM portfolio ORDER BY id DESC LIMIT 1")
            portfolio = cursor.fetchone()
            
            freed_margin = qty * avg_cost
            new_avail = portfolio[2] + freed_margin + realized_pnl
            new_total_capital = portfolio[1] + realized_pnl
            new_used_margin = max(0, portfolio[3] - freed_margin)
            new_total_pnl = portfolio[4] + realized_pnl
            
            cursor.execute('''UPDATE portfolio 
                              SET total_capital=?, available_balance=?, used_margin=?, total_pnl=?, last_updated=? 
                              WHERE id=?''', 
                           (new_total_capital, new_avail, new_used_margin, new_total_pnl, now, portfolio[0]))
                           
            conn.commit()
            return {"success": True, "message": f"{symbol} pozisyonu kapatıldı. K/Z: {realized_pnl:.2f} TL (%{pnl_pct:.2f})"}
            
        except Exception as e:
            conn.rollback()
            logger.error(f"Close Position Error: {e}")
            return {"success": False, "message": str(e)}
        finally:
            conn.close()

    def update_market_prices(self, current_prices: dict):
        """Updates unrealized PnL for active positions."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        try:
            for symbol, current_price in current_prices.items():
                cursor.execute("SELECT id, direction, quantity, average_cost FROM active_positions WHERE symbol=?", (symbol,))
                pos = cursor.fetchone()
                if pos:
                    direction = pos[1]
                    qty = pos[2]
                    avg_cost = pos[3]
                    
                    if direction == 'LONG':
                        unrealized_pnl = (current_price - avg_cost) * qty
                    else:
                        unrealized_pnl = (avg_cost - current_price) * qty
                        
                    cursor.execute("UPDATE active_positions SET current_price=?, unrealized_pnl=?, last_updated=? WHERE id=?",
                                   (current_price, unrealized_pnl, datetime.now().isoformat(), pos[0]))
            conn.commit()
        except Exception as e:
            logger.error(f"Update Prices Error: {e}")
        finally:
            conn.close()

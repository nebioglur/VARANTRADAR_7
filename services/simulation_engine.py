import pandas as pd
from datetime import datetime, time, timedelta
import json
from services.trade_database import get_connection
from services.market_data import MarketDataManager

class SimulationEngine:
    """
    Backtest Motoru:
    - Sinyalleri okur.
    - Market datasını okur.
    - Zaman ekseninde (bar bar) ilerler ve işlemleri gerçekleştirir.
    - Trade geçmişini ve Equity curve'ü veritabanına yazar.
    """
    
    def __init__(self, daily_budget=10000.0, max_positions=15):
        self.daily_budget = daily_budget
        self.max_positions = max_positions
        
    def _save_trades(self, date_str: str, trades: list):
        conn = get_connection()
        cursor = conn.cursor()
        for t in trades:
            try:
                cursor.execute("""
                    INSERT INTO trades (date_str, symbol, entry_time, entry_price, exit_time, exit_price, shares, pnl_val, pnl_pct, exit_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(date_str, symbol, entry_time) DO UPDATE SET
                        exit_time=excluded.exit_time,
                        exit_price=excluded.exit_price,
                        pnl_val=excluded.pnl_val,
                        pnl_pct=excluded.pnl_pct,
                        exit_reason=excluded.exit_reason
                """, (
                    date_str, t['symbol'], t['entry_time'], t['entry_price'], 
                    t.get('exit_time'), t.get('exit_price'), t.get('shares'),
                    t.get('pnl_val'), t.get('pnl_pct'), t.get('exit_reason')
                ))
            except Exception as e:
                print(f"[SimEngine] Trade save err {t['symbol']}: {e}")
                
        # Equity Log
        total_pnl = sum(t.get('pnl_val', 0) for t in trades if t.get('exit_time'))
        win_trades = sum(1 for t in trades if t.get('pnl_val', 0) > 0)
        
        try:
            cursor.execute("""
                INSERT INTO equity_log (date_str, start_equity, end_equity, daily_pnl, total_trades, win_trades)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date_str) DO UPDATE SET
                    end_equity=excluded.end_equity,
                    daily_pnl=excluded.daily_pnl,
                    total_trades=excluded.total_trades,
                    win_trades=excluded.win_trades
            """, (
                date_str, self.daily_budget, self.daily_budget + total_pnl, 
                total_pnl, len(trades), win_trades
            ))
        except Exception as e:
            print(f"[SimEngine] Equity save err: {e}")
            
        conn.commit()
        conn.close()

    def _check_ema_stop(self, sub_df):
        """ EMA8 < EMA21 kesişimi olup olmadığını kontrol eder """
        if len(sub_df) < 21:
            return False, ""
            
        close = sub_df['Close']
        ema8 = close.ewm(span=8, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()
        
        c_ema8 = float(ema8.iloc[-1])
        c_ema21 = float(ema21.iloc[-1])
        p_ema8 = float(ema8.iloc[-2]) if len(ema8) > 1 else c_ema8
        p_ema21 = float(ema21.iloc[-2]) if len(ema21) > 1 else c_ema21
        
        crossed_down = (p_ema8 >= p_ema21) and (c_ema8 < c_ema21)
        momentum = close.iloc[-1] - (close.iloc[-10] if len(close) > 10 else close.iloc[0])
        
        if crossed_down or (c_ema8 < c_ema21 and momentum < 0):
            return True, "📉 AL Puanı < 50 (Trend Bozuldu)"
            
        return False, ""

    def run_daily_simulation(self, date_str: str):
        signals = MarketDataManager.get_signals(date_str)
        if not signals:
            print(f"[SimEngine] {date_str} için sinyal yok.")
            return

        # Sadece Skoru >= 80 ve Uptrend olanları al
        valid_signals = []
        for s in signals:
            score = float(s['score'])
            phase = str(s['morning_phase'])
            if score >= 80 and "YATAY" not in phase and "NEGATİF" not in phase and "UZAK DUR" not in phase:
                valid_signals.append(s)
                
        # En iyi 15
        selected = valid_signals[:self.max_positions]
        if not selected:
            return
            
        # Para yönetimi
        total_score = sum(s['score'] for s in selected)
        if total_score == 0: total_score = 1
        
        active_trades = []
        # Tüm DF leri çek ve hazırla
        dfs = {}
        for s in selected:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)
            if not df.empty:
                dfs[sym] = df
                allocation = self.daily_budget * (s['score'] / total_score)
                entry_price = s['morning_price']
                if entry_price > 0:
                    shares = int(allocation // entry_price)
                    if shares > 0:
                        active_trades.append({
                            'symbol': sym,
                            'entry_time': f"{date_str} 10:15:00",
                            'entry_price': entry_price,
                            'ceiling_target': s['ceiling_target'],
                            'shares': shares,
                            'status': 'OPEN'
                        })

        if not active_trades:
            return
            
        # Tüm günün eşsiz zaman damgalarını bul
        all_times = set()
        for df in dfs.values():
            for t in df.index:
                all_times.add(t)
                
        sorted_times = sorted(list(all_times))
        
        # Simülasyon Döngüsü (Zaman Ekseninde İlerle)
        completed_trades = []
        
        for current_time in sorted_times:
            # Sadece 10:15 sonrasını değerlendir
            if current_time.time() < time(10, 15):
                continue
                
            for trade in [t for t in active_trades if t['status'] == 'OPEN']:
                sym = trade['symbol']
                df = dfs[sym]
                
                # Bu hisse o anki zamanda veriye sahip mi?
                if current_time not in df.index:
                    continue
                    
                sub_df = df.loc[:current_time]
                row = df.loc[current_time]
                
                elapsed_mins = (current_time - pd.to_datetime(trade['entry_time'])).total_seconds() / 60.0
                high = float(row['High'])
                low = float(row['Low'])
                close = float(row['Close'])
                
                sell_price = None
                reason = ""
                
                # Kural 1: Hard Stop Loss (-2%)
                if low <= trade['entry_price'] * 0.98:
                    sell_price = trade['entry_price'] * 0.98
                    reason = "🛡️ ZARAR KES (-2%)"
                    
                # Kural 2: Take Profit (Tavan)
                elif high >= trade['ceiling_target']:
                    sell_price = trade['ceiling_target']
                    reason = "🚀 TAVAN (MAKS KÂR)"
                    
                # Kural 3: Minimum 30 dk şartını geçtikten sonra Trend Kesişimi veya Max Time
                elif elapsed_mins >= 30:
                    if elapsed_mins >= 480: # 8 Saat
                        sell_price = close
                        reason = "⏱️ ZAMAN AŞIMI (8 SAAT)"
                    else:
                        is_stop, stop_reason = self._check_ema_stop(sub_df)
                        if is_stop:
                            sell_price = close
                            reason = stop_reason
                            
                # Eğer satış kararı verildiyse işlemi kapat
                if sell_price is not None:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(current_time)
                    trade['exit_price'] = sell_price
                    trade['pnl_val'] = trade['shares'] * (sell_price - trade['entry_price'])
                    trade['pnl_pct'] = ((sell_price - trade['entry_price']) / trade['entry_price']) * 100
                    trade['exit_reason'] = reason
                    completed_trades.append(trade)

        # Gün bittiğinde hala açık olanları kapanıştan sat
        for trade in [t for t in active_trades if t['status'] == 'OPEN']:
            sym = trade['symbol']
            df = dfs[sym]
            if not df.empty:
                last_time = df.index[-1]
                close = float(df.iloc[-1]['Close'])
                
                trade['status'] = 'CLOSED'
                trade['exit_time'] = str(last_time)
                trade['exit_price'] = close
                trade['pnl_val'] = trade['shares'] * (close - trade['entry_price'])
                trade['pnl_pct'] = ((close - trade['entry_price']) / trade['entry_price']) * 100
                
                if last_time.time() < time(18, 0):
                    trade['exit_reason'] = "⏳ SEANS BEKLENİYOR"
                else:
                    trade['exit_reason'] = "⏱️ GÜN SONU KAPANAN"
                
                completed_trades.append(trade)

        # Veritabanına kaydet
        self._save_trades(date_str, completed_trades)
        print(f"[SimEngine] {date_str} için SİMÜLASYON tamamlandı. İşlem Sayısı: {len(completed_trades)}")

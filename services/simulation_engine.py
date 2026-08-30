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
            cursor.execute("SELECT end_equity FROM equity_log ORDER BY date_str DESC LIMIT 1")
            prev = cursor.fetchone()
            start_eq = float(prev['end_equity']) if prev else self.daily_budget
        except Exception as e:
            start_eq = self.daily_budget

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
                date_str, start_eq, start_eq + total_pnl, 
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
            return

        valid_signals = []
        import json
        for s in signals:
            score = float(s.get('score', 0) or 0)
            phase = str(s.get('morning_phase', '') or '')
            
            # KULLANICI İSTEĞİ: SİMULASYONDA EMA 50 EMA 200 ÜSTÜ FILTRESİNE UYAN HİSSELERİ ELE AL
            metadata_str = s.get('metadata')
            meta = {}
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                except Exception as e_meta:
                    print(f"[SimEngine] Metadata parse hatası {s.get('symbol', '?')}: {e_meta}")
            
            price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
            
            # EMA değerlerini birden fazla olası anahtardan ara
            ema50 = meta.get('Daily_EMA50')
            ema200 = meta.get('Daily_EMA200')
            
            if ema50 is None or ema200 is None:
                indicators = meta.get('Indicators', {})
                ema50 = ema50 or indicators.get('EMA_50') or indicators.get('EMA_50')
                ema200 = ema200 or indicators.get('EMA_200') or indicators.get('EMA_200')
                    
            if ema50 and ema200 and price:
                try:
                    if float(price) <= float(ema50) or float(price) <= float(ema200):
                        continue # EMA filtrelerine uymadığı için simülasyona alınmaz
                except (ValueError, TypeError):
                    pass  # Dönüşüm hatası olursa filtreyi atla
                    
            if score >= 80 and "YATAY" not in phase and "NEGATİF" not in phase and "UZAK DUR" not in phase:
                valid_signals.append(s)
                
        selected = valid_signals
        if not selected:
            return
            
        current_cash = self.daily_budget
        # Çelik Sistem: İşlem başına max zarar 100 TL. Stop = %3. 
        # İdeal Sermaye = 100 / 0.03 = 3333 TL.
        ideal_allocation = 3333.0 
        
        active_trades = []
        completed_trades = []
        stopped_out_symbols = set()
        
        pending_signals = []
        dfs = {}
        all_times = set()
        
        for s in selected:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)
            if not df.empty:
                dfs[sym] = df
                for t in df.index:
                    all_times.add(t)
                
                phase = str(s.get('morning_phase', ''))
                import re
                match = re.search(r'(\d{2}:\d{2})', phase)
                time_str = match.group(1) + ":00" if match else "10:15:00"
                
                s['time_str'] = time_str
                pending_signals.append(s)
                
        sorted_times = sorted(list(all_times))
        
        for current_time in sorted_times:
            # 1. SATIŞLARI KONTROL ET (Zincir Emirler - OCO)
            for trade in [t for t in active_trades if t['status'] == 'OPEN']:
                sym = trade['symbol']
                df = dfs[sym]
                
                if current_time not in df.index: continue
                
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                dt_entry = pd.to_datetime(trade['entry_time'])
                dt_entry = dt_entry.tz_localize(None) if dt_entry.tzinfo else dt_entry
                if dt_current < dt_entry: continue
                
                row = df.loc[current_time]
                high = float(row['High'])
                low = float(row['Low'])
                close = float(row['Close'])
                
                sell_price = None
                reason = ""
                
                entry = trade['entry_price']
                
                # Çelik Hedefler (Gerçek hayatta Zincir Emir olarak bankaya girilir)
                stop_price = trade['stop_price']
                tp1_price = trade['tp1_price']
                tp2_price = trade['tp2_price']
                
                # En kötü senaryo: Önce Stop Loss patlar varsayımı
                if low <= stop_price:
                    sell_price = stop_price * 0.9985 # Slipaj
                    reason = f"⛔ ÇELİK STOP KESİLDİ (-%3)"
                elif high >= tp2_price:
                    sell_price = tp2_price
                    reason = f"🚀 TAVAN (TAM KÂR ALINDI)"
                elif high >= tp1_price and not trade.get('scaled_out', False):
                    # Yarısını Kâr Al (TP1)
                    trade['scaled_out'] = True
                    half_shares = trade['shares'] // 2
                    if half_shares > 0:
                        trade['shares'] -= half_shares
                        scale_out_price = tp1_price * 0.9985
                        buy_vol = half_shares * entry
                        sell_vol = half_shares * scale_out_price
                        comm = (buy_vol + sell_vol) * 0.0004
                        net_profit = (half_shares * (scale_out_price - entry)) - comm
                        current_cash += sell_vol - comm 
                        
                        # Artık geride kalan lotlar için stop başa (maliyete) çekilir! (Risk Free)
                        trade['stop_price'] = entry 
                        
                        completed_trades.append({
                            'symbol': sym,
                            'entry_time': trade['entry_time'],
                            'entry_price': entry,
                            'shares': half_shares,
                            'exit_time': str(current_time),
                            'exit_price': scale_out_price,
                            'pnl_val': net_profit,
                            'pnl_pct': (net_profit / buy_vol) * 100,
                            'exit_reason': "⚖️ ÇELİK TP1 (YARISI SATILDI)"
                        })
                            
                if sell_price is not None:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(current_time)
                    trade['exit_price'] = sell_price
                    
                    buy_volume = trade['shares'] * trade['entry_price']
                    sell_volume = trade['shares'] * sell_price
                    commission = (buy_volume + sell_volume) * 0.0004
                    gross_pnl = trade['shares'] * (sell_price - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl - commission
                    trade['pnl_pct'] = (trade['pnl_val'] / buy_volume) * 100
                    
                    if "🔄" not in trade.get('exit_reason', '') and trade.get('is_reentry', False):
                        reason = "🔄 " + reason
                        
                    trade['exit_reason'] = reason
                    completed_trades.append(trade)
                    
                    if "STOP" in reason:
                        stopped_out_symbols.add(sym)
                        
                    current_cash += sell_volume - commission
                    
            # 2. YENİ ALIMLARI KONTROL ET
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}
            
            to_remove = []
            for s in pending_signals:
                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current >= dt_ps:
                    to_remove.append(s)
                    if s['symbol'] in open_symbols:
                        continue
                        
                    # "Squaze (yukarı ok) + Güçlü Giriş + Pozitif Alpha" Kontrolü
                    alpha_str = str(s.get("Alpha_Str", ""))
                    sqz_str = str(s.get("Short_Squeeze", ""))
                    sm_str = str(s.get("Smart_Money", ""))
                    
                    is_super_green = (
                        "Pozitif" in alpha_str and 
                        ("Giriş" in sm_str or "Akümülasyon" in sm_str) and 
                        ("Yükseliyor" in sqz_str or "Patlatma" in sqz_str)
                    )
                    
                    if is_super_green:
                        allocation = min(current_cash, self.daily_budget) # Tam sermaye (Maksimum Giriş)
                    else:
                        allocation = min(current_cash, ideal_allocation)
                        
                    if allocation >= 1000:
                        sym = s['symbol']
                        df = dfs.get(sym)
                        if df is not None and current_time in df.index:
                            raw_entry = float(df.loc[current_time, 'Close'])
                            ceiling = float(s.get('ceiling_target', 0) or 0)
                            if ceiling <= 0:
                                ceiling = raw_entry * 1.10  # Fallback: +%10 hedef
                            prev_close = ceiling / 1.10
                            
                            if raw_entry >= prev_close * 1.095:
                                continue
                                
                            entry_price = raw_entry * 1.0015
                            shares = int(allocation // entry_price)
                            if shares > 0:
                                current_cash -= (shares * entry_price) * 1.0004 
                                active_trades.append({
                                    'symbol': sym,
                                    'entry_time': str(current_time),
                                    'entry_price': entry_price,
                                    'ceiling_target': ceiling,
                                    'stop_price': entry_price * 0.97, # Çelik Kural: -%3 Zarar Kes
                                    'tp1_price': entry_price * 1.05,  # Çelik Kural: +%5 Kâr Al (Yarısı)
                                    'tp2_price': ceiling,             # Çelik Kural: Tavan Kâr Al
                                    'shares': shares,
                                    'status': 'OPEN',
                                    'scaled_out': False,
                                    'is_reentry': False
                                })
            for s in to_remove:
                if s in pending_signals:
                    pending_signals.remove(s)
                    
            # 3. YENİDEN GİRİŞ (Trend Dönerse, Sadece Stop olanlar için)
            # Re-entry de sabit zincir emirle olur
            # Not: Re-entry manuel işlemlerde zor olabilir, ama sistemi 'çelik' kılanlardan biri bu
            # Kestik attık ama trend dönerse alarm çalar!
            for sym in list(stopped_out_symbols):
                if sym not in open_symbols:
                    sig = next((x for x in selected if x['symbol'] == sym), None)
                    is_super_green = False
                    if sig:
                        alpha_str = str(sig.get("Alpha_Str", ""))
                        sqz_str = str(sig.get("Short_Squeeze", ""))
                        sm_str = str(sig.get("Smart_Money", ""))
                        is_super_green = (
                            "Pozitif" in alpha_str and 
                            ("Giriş" in sm_str or "Akümülasyon" in sm_str) and 
                            ("Yükseliyor" in sqz_str or "Patlatma" in sqz_str)
                        )
                        
                    if is_super_green:
                        allocation = min(current_cash, self.daily_budget)
                    else:
                        allocation = min(current_cash, ideal_allocation)
                        
                    if allocation >= 1000:
                        df = dfs.get(sym)
                        if df is not None and current_time in df.index:
                            sub_df = df.loc[:current_time]
                            if len(sub_df) >= 21:
                                close_series = sub_df['Close']
                                ema8 = close_series.ewm(span=8, adjust=False).mean()
                                ema21 = close_series.ewm(span=21, adjust=False).mean()
                                c_ema8 = float(ema8.iloc[-1])
                                c_ema21 = float(ema21.iloc[-1])
                                p_ema8 = float(ema8.iloc[-2])
                                p_ema21 = float(ema21.iloc[-2])
                                
                                if p_ema8 <= p_ema21 and c_ema8 > c_ema21:
                                    raw_entry = float(close_series.iloc[-1])
                                    entry_price = raw_entry * 1.0015
                                    shares = int(allocation // entry_price)
                                    if shares > 0:
                                        current_cash -= (shares * entry_price) * 1.0004
                                        active_trades.append({
                                            'symbol': sym,
                                            'entry_time': str(current_time),
                                            'entry_price': entry_price,
                                            'ceiling_target': entry_price * 1.10, 
                                            'stop_price': entry_price * 0.97,
                                            'tp1_price': entry_price * 1.05,
                                            'tp2_price': entry_price * 1.10,
                                            'shares': shares,
                                            'status': 'OPEN',
                                            'scaled_out': False,
                                            'is_reentry': True
                                        })
                                        stopped_out_symbols.remove(sym)

        for trade in [t for t in active_trades if t['status'] == 'OPEN']:
            sym = trade['symbol']
            df = dfs[sym]
            if not df.empty:
                last_time = df.index[-1]
                close = float(df.iloc[-1]['Close'])
                trade['status'] = 'CLOSED'
                trade['exit_time'] = str(last_time)
                trade['exit_price'] = close
                buy_volume = trade['shares'] * trade['entry_price']
                sell_volume = trade['shares'] * close
                commission = (buy_volume + sell_volume) * 0.0004
                gross_pnl = trade['shares'] * (close - trade['entry_price'])
                trade['pnl_val'] = gross_pnl - commission
                trade['pnl_pct'] = (trade['pnl_val'] / buy_volume) * 100
                if last_time.time() < time(18, 0):
                    trade['exit_reason'] = "⏳ SEANS BEKLENİYOR"
                else:
                    trade['exit_reason'] = "⏱️ GÜN SONU KAPANAN"
                completed_trades.append(trade)

        self._save_trades(date_str, completed_trades)
        print(f"[SimEngine] {date_str} için ÇELİK SİSTEM tamamlandı. İşlem Sayısı: {len(completed_trades)}")

import pandas as pd
import os
from datetime import datetime, time, timedelta
import json
from services.trade_database import get_connection
from services.market_data import MarketDataManager

class SimulationEngine:
    _daily_trend_cache = None

    """
    Backtest Motoru:
    - Sinyalleri okur.
    - Market datasını okur.
    - Zaman ekseninde (bar bar) ilerler ve işlemleri gerçekleştirir.
    - Trade geçmişini ve Equity curve'ü veritabanına yazar.
    """
    
    def __init__(self, daily_budget=100000.0, max_positions=15, owner=None):
        self.daily_budget = daily_budget
        self.max_positions = max_positions
        self.owner = owner or "local:nebioglur"

    def _save_trades(self, date_str: str, trades: list):
        # Ayni (sembol, giris dakikasi) icin birden fazla cikis bacagi olusabilir
        # (TP1 kismi + kalan pozisyon stopu gibi). DB tek satir tutabildigi icin
        # ezilen bacak PnL kayboluyordu; bacaklari tek kayitta birlestir.
        merged = {}
        order = []
        for t in trades:
            key = (t['symbol'], t['entry_time'])
            if key not in merged:
                merged[key] = dict(t)
                order.append(key)
                continue
            m = merged[key]
            m['shares'] = int(m.get('shares') or 0) + int(t.get('shares') or 0)
            m['pnl_val'] = float(m.get('pnl_val') or 0) + float(t.get('pnl_val') or 0)
            buy_vol = int(m.get('shares') or 0) * float(m.get('entry_price') or 0)
            m['pnl_pct'] = (m['pnl_val'] / buy_vol * 100) if buy_vol > 0 else 0
            m['exit_time'] = t.get('exit_time') or m.get('exit_time')
            m['exit_price'] = t.get('exit_price') or m.get('exit_price')
            m['exit_reason'] = f"{m.get('exit_reason', '')} + {t.get('exit_reason', '')}".strip(' +')

        conn = get_connection()
        cursor = conn.cursor()
        # Idempotent yeniden calistirma: ayni gunun eski islemleri temizlenir,
        # boylece farkli motor surumlerinin kayitlari karismaz.
        try:
            cursor.execute("DELETE FROM trades WHERE owner=? AND date_str=?", (self.owner, date_str))
        except Exception as e:
            print(f"[SimEngine] Eski trade temizleme hatasi: {e}")
        for key in order:
            t = merged[key]
            try:
                cursor.execute("""
                    INSERT INTO trades (
                        owner, date_str, symbol, entry_time, entry_price, exit_time,
                        exit_price, shares, pnl_val, pnl_pct, exit_reason, strategy_name,
                        entry_score, entry_checks, atr_value, risk_amount, market_regime
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, date_str, symbol, entry_time) DO UPDATE SET
                        exit_time=excluded.exit_time,
                        exit_price=excluded.exit_price,
                        pnl_val=excluded.pnl_val,
                        pnl_pct=excluded.pnl_pct,
                        exit_reason=excluded.exit_reason,
                        strategy_name=excluded.strategy_name,
                        entry_score=excluded.entry_score,
                        entry_checks=excluded.entry_checks,
                        atr_value=excluded.atr_value,
                        risk_amount=excluded.risk_amount,
                        market_regime=excluded.market_regime
                """, (
                    self.owner, date_str, t['symbol'], t['entry_time'], t['entry_price'],
                    t.get('exit_time'), t.get('exit_price'), t.get('shares'),
                    t.get('pnl_val'), t.get('pnl_pct'), t.get('exit_reason'),
                    t.get('strategy_name'), t.get('entry_score'), t.get('entry_checks'),
                    t.get('atr_value'), t.get('risk_amount'), t.get('market_regime')
                ))
            except Exception as e:
                print(f"[SimEngine] Trade save err {t['symbol']}: {e}")

        # Equity Log (hesap bazli) - birlestirilmis kayitlar uzerinden;
        # boylece equity_log ile trades tablosu SUM'u daima tutarli olur.
        total_pnl = sum(t.get('pnl_val', 0) for t in merged.values() if t.get('exit_time'))
        win_trades = sum(1 for t in merged.values() if t.get('pnl_val', 0) > 0)

        try:
            # Bakiye zinciri: yalnizca ONCEKI GUNUN bitisi baz alinir.
            # (Bugunun satiri okunursa ayni gun tekrar calistirmada kar
            #  uzerine kar eklenir ve zincir sasardi.)
            cursor.execute(
                "SELECT end_equity FROM equity_log WHERE owner=? AND date_str<? ORDER BY date_str DESC LIMIT 1",
                (self.owner, date_str)
            )
            prev = cursor.fetchone()
            start_eq = float(prev['end_equity']) if prev else self.daily_budget
        except Exception as e:
            start_eq = self.daily_budget

        try:
            cursor.execute("""
                INSERT INTO equity_log (owner, date_str, start_equity, end_equity, daily_pnl, total_trades, win_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner, date_str) DO UPDATE SET
                    start_equity=excluded.start_equity,
                    end_equity=excluded.end_equity,
                    daily_pnl=excluded.daily_pnl,
                    total_trades=excluded.total_trades,
                    win_trades=excluded.win_trades
            """, (
                self.owner, date_str, start_eq, start_eq + total_pnl,
                total_pnl, len(order), win_trades
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

    def _entry_setup(self, sub_df, entry_price):
        # 5dk veride sinyal saatinde (or. 10:15) 22 bar yok; esnek olmak icin
        # minimum 12 bar (1 saat) yeterli. EMA21 hesaplanamazsa EMA9 trendi kullanilir.
        if len(sub_df) < 12:
            return None

        close = pd.to_numeric(sub_df['Close'], errors='coerce').dropna()
        high = pd.to_numeric(sub_df['High'], errors='coerce').reindex(close.index)
        low = pd.to_numeric(sub_df['Low'], errors='coerce').reindex(close.index)
        if len(close) < 12 or high.isna().any() or low.isna().any():
            return None

        ema9 = close.ewm(span=9, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()

        ema9_ok = ema9.iloc[-1] > ema9.iloc[-2] and close.iloc[-1] >= ema9.iloc[-1]
        if len(ema21.dropna()) >= 2:
            ema_confirmed = ema9_ok and (ema9.iloc[-1] > ema21.iloc[-1])
        else:
            # EMA21 henuz guvenilir degilse sadece EMA9 momentumuyla ilerle
            ema_confirmed = ema9_ok
        if not ema_confirmed:
            return None

        prev_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr = float(true_range.rolling(14, min_periods=5).mean().iloc[-1])
        if not pd.notna(atr) or atr <= 0:
            return None

        stop_pct = min(0.045, max(0.015, (atr / entry_price) * 1.6))
        stop_price = entry_price * (1 - stop_pct)
        return {
            'atr_value': atr,
            'stop_pct': stop_pct,
            'stop_price': stop_price,
            'ema9': float(ema9.iloc[-1]),
            'ema21': float(ema21.iloc[-1]) if len(ema21.dropna()) >= 1 else None
        }

    @classmethod
    def _daily_trend_values(cls, meta, symbol):
        indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
        ema50 = meta.get('Daily_EMA50') or indicators.get('EMA_50')
        ema200 = meta.get('Daily_EMA200') or indicators.get('EMA_200')
        if ema50 and ema200:
            return float(ema50), float(ema200)

        if cls._daily_trend_cache is None:
            cls._daily_trend_cache = {}
            try:
                with open('dashboard_cache.json', encoding='utf-8') as cache_file:
                    cached = json.load(cache_file)
                cls._daily_trend_cache = cached.get('all_symbols_stats', {})
            except Exception:
                pass

        cached = cls._daily_trend_cache.get(symbol) or cls._daily_trend_cache.get(symbol.replace('.IS', ''))
        if not isinstance(cached, dict):
            return None, None
        ema50 = cached.get('Daily_EMA50')
        ema200 = cached.get('Daily_EMA200')
        if not ema50 or not ema200:
            return None, None
        return float(ema50), float(ema200)

    def _position_allocation(self, current_cash, entry_price, stop_price, is_bear):
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return 0.0, 0.0

        risk_budget = self.daily_budget * (0.0035 if is_bear else 0.0075)
        max_notional = self.daily_budget * (0.10 if is_bear else 0.20)
        risk_limited_notional = risk_budget * entry_price / risk_per_share
        allocation = min(current_cash, max_notional, risk_limited_notional)
        return allocation, min(risk_budget, allocation * risk_per_share / entry_price)

    def run_daily_simulation(self, date_str: str):
        signals = MarketDataManager.get_signals(date_str)
        if not signals:
            return

        try:
            from server import get_xu100_change
            xu100_change = float(get_xu100_change())
        except Exception:
            xu100_change = 0.0
        is_bear = xu100_change < -0.5
        market_regime = "AYI" if is_bear else ("GÜÇLÜ POZİTİF" if xu100_change > 0.5 else "NÖTR")
        minimum_score = 90 if is_bear else 85

        valid_signals = []
        import json
        for s in signals:
            score = float(s['score'])
            phase = str(s['morning_phase'])
            
            # KULLANICI İSTEĞİ: SİMULASYONDA EMA 50 EMA 200 ÜSTÜ FILTRESİNE UYAN HİSSELERİ ELE AL
            metadata_str = s.get('metadata')
            meta = {}
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                except Exception as e_meta:
                    print(f"[SimEngine] Metadata parse hatası {s.get('symbol', '?')}: {e_meta}")
            
            price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
            
            ema50, ema200 = self._daily_trend_values(meta, s['symbol'])
                    
            # EMA Filtresi ZORUNLU
            if not ema50 or not ema200 or not price:
                continue # Veri eksikse atla
            try:
                if float(price) <= float(ema50) or float(price) <= float(ema200):
                    continue # Fiyat EMA altında
            except (ValueError, TypeError):
                continue # Dönüşüm hatası
                    
            if score >= minimum_score and phase in ["Erken Kopuş (Phase 1)", "İvmelenme (Phase 2)", "Kilitleme Baskısı (Phase 3)"]:
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
                volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
                details = [str(detail) for detail in meta.get('Details', [])]
                detail_text = " ".join(details).upper()
                macd_value = indicators.get('MACD_Positive')
                macd_ok = bool(macd_value) if macd_value is not None else "MACD" in detail_text
                vwap = meta.get('VWAP')
                vwap_ok = bool(vwap) and price >= float(vwap)
                fomo_score = float(meta.get('FOMO_Score') or 0)
                no_trap = not bool(meta.get('Trap_Risk'))
                fomo_ok = fomo_score < 90 or (
                    volume_multiplier >= 2.0
                    and ("Giriş" in str(meta.get("Smart_Money", "")) or "Akümülasyon" in str(meta.get("Smart_Money", "")))
                )
                sector_ok = bool(meta.get('Domino_Sector')) or "SEKTÖR GÜCÜ" in detail_text
                volume_ok = volume_multiplier >= 1.0 or "HACİMLİ" in detail_text
                checks = {
                    "Ana trend": True,
                    "RSI dengeli": 32 <= rsi <= 82,
                    "Hacim teyidi": volume_ok,
                    "MACD yönü": macd_ok,
                    "VWAP üstü": vwap_ok,
                    "Tuzak/FOMO temiz": no_trap,
                    "Sektör desteği": sector_ok,
                    "FOMO kontrollü": fomo_ok
                }
                if sum(checks.values()) < 5 or not checks["RSI dengeli"] or not checks["Hacim teyidi"] or not checks["Tuzak/FOMO temiz"]:
                    continue
                s['_entry_checks'] = ", ".join(name for name, passed in checks.items() if passed)
                s['_entry_quality'] = sum(checks.values())
                s['_metadata'] = meta
                valid_signals.append(s)
                
        valid_signals.sort(key=lambda x: float(x.get('score', 0)), reverse=True)
        selected = valid_signals[:min(5, self.max_positions)]
        if not selected:
            return

        current_cash = self.daily_budget
        
        active_trades = []
        completed_trades = []
        stopped_out_symbols = set()
        stop_times = {}
        
        pending_signals = []
        dfs = {}
        all_times = set()
        
        for s in selected:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)
            if not df.empty:
                # Karma tz verisi: Postgres timestamp'leri tz-aware, yfinance
                # verisi naive geliyor; sorted() bu karisimda patliyor.
                # Tum indeksleri naive'e cevir (sutun karsilastirmalari zaten
                # kodun geri kalaninda naive varsayiyor).
                if getattr(df.index, 'tz', None) is not None:
                    df.index = df.index.tz_localize(None)
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
                
                # DİNAMİK İZLEYEN STOP (Trailing Stop)
                # Kâr > %2 ise stopu maliyete (Sıfıra) çek
                if high >= entry * 1.02 and trade['stop_price'] < entry * 1.002:
                    trade['stop_price'] = entry * 1.002
                    trade['reason_prefix'] = "[İZLEYEN STOP AKTİF] "
                
                # Kâr > %3 ise stopu maliyete taşı; kazananı kaybedene dönüştürme
                if high >= entry * 1.03 and trade['stop_price'] < entry * 1.001:
                    trade['stop_price'] = entry * 1.001
                    trade['reason_prefix'] = "[KÂR KORUMA AKTİF] "

                # Kâr > %5 ise en az %2 kârı kilitle
                if high >= entry * 1.05 and trade['stop_price'] < entry * 1.02:
                    trade['stop_price'] = entry * 1.02
                    trade['reason_prefix'] = "[KÂR KİLİTLENDİ] "

                stop_price = trade['stop_price']
                tp1_price = trade['tp1_price']
                tp2_price = trade['tp2_price']
                prefix = trade.get('reason_prefix', '')
                
                # En kötü senaryo: Önce Stop Loss patlar varsayımı
                if low <= stop_price:
                    sell_price = stop_price * 0.9985 # Slipaj
                    reason = f"{prefix}⛔ ÇELİK STOP KESİLDİ"
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
                            'exit_reason': "⚖️ ÇELİK TP1 (YARISI SATILDI)",
                            'strategy_name': trade.get('strategy_name'),
                            'entry_score': trade.get('entry_score'),
                            'entry_checks': trade.get('entry_checks'),
                            'atr_value': trade.get('atr_value'),
                            'risk_amount': trade.get('risk_amount'),
                            'market_regime': trade.get('market_regime')
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
                        stop_times[sym] = current_time
                        
                    current_cash += sell_volume - commission
                    
            # 2. YENİ ALIMLARI KONTROL ET
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}
            
            to_remove = []
            for s in pending_signals:
                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current < dt_ps:
                    continue
                if dt_current.time() >= time(17, 50):
                    to_remove.append(s)
                    continue
                if s['symbol'] in open_symbols or len(open_symbols) >= self.max_positions:
                    continue

                sym = s['symbol']
                df = dfs.get(sym)
                if df is None or current_time not in df.index:
                    continue

                # Verisi erken kesilen hissede islem acma (veri saglayici
                # bazi sembollerde gunu yari yolda bitiriyor; giris=çikis
                # ayni dakika kaliyordu). Yine de erken saatlerde pozisyon
                # acilabilmesi icin en az 3 bar (15 dk) yonetilebilir veri sart.
                remaining_bars = int((df.index > current_time).sum())
                if remaining_bars < 3:
                    to_remove.append(s)
                    continue

                raw_entry = float(df.loc[current_time, 'Close'])
                ceiling = float(s['ceiling_target'])
                prev_close = ceiling / 1.10
                if raw_entry >= prev_close * 1.095:
                    to_remove.append(s)
                    continue

                entry_price = raw_entry * 1.0015
                setup = self._entry_setup(df.loc[:current_time], entry_price)
                if not setup:
                    continue

                tp1_price = min(ceiling * 0.997, entry_price + max(setup['atr_value'] * 1.8, entry_price * 0.025))
                if tp1_price <= entry_price:
                    to_remove.append(s)
                    continue
                allocation, risk_amount = self._position_allocation(
                    current_cash, entry_price, setup['stop_price'], is_bear
                )
                shares = int(allocation // entry_price)
                if shares <= 0:
                    to_remove.append(s)
                    continue

                current_cash -= (shares * entry_price) * 1.0004
                active_trades.append({
                    'symbol': sym,
                    'entry_time': str(current_time),
                    'entry_price': entry_price,
                    'ceiling_target': ceiling,
                    'stop_price': setup['stop_price'],
                    'tp1_price': tp1_price,
                    'tp2_price': ceiling,
                    'shares': shares,
                    'status': 'OPEN',
                    'scaled_out': False,
                    'is_reentry': False,
                    'strategy_name': 'EMA 9/21 + Kalite Kapısı',
                    'entry_score': float(s.get('score', 0)),
                    'entry_checks': s.get('_entry_checks', ''),
                    'atr_value': setup['atr_value'],
                    'risk_amount': risk_amount,
                    'market_regime': market_regime
                })
                to_remove.append(s)
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
                    stopped_at = stop_times.get(sym)
                    if not sig or not stopped_at or dt_current - stopped_at < timedelta(minutes=60):
                        continue
                    if dt_current.time() >= time(17, 0):
                        continue
                    df = dfs.get(sym)
                    if df is None or current_time not in df.index:
                        continue
                    # Erken kesilen veride yeniden giris de yapma
                    if int((df.index > current_time).sum()) < 3:
                        continue
                    sub_df = df.loc[:current_time]
                    raw_entry = float(sub_df['Close'].iloc[-1])
                    entry_price = raw_entry * 1.0015
                    setup = self._entry_setup(sub_df, entry_price)
                    if not setup:
                        continue
                    allocation, risk_amount = self._position_allocation(
                        current_cash, entry_price, setup['stop_price'], is_bear
                    )
                    shares = int(allocation // entry_price)
                    if shares <= 0:
                        continue
                    current_cash -= (shares * entry_price) * 1.0004
                    active_trades.append({
                        'symbol': sym,
                        'entry_time': str(current_time),
                        'entry_price': entry_price,
                        'ceiling_target': entry_price * 1.10,
                        'stop_price': setup['stop_price'],
                        'tp1_price': entry_price + max(setup['atr_value'] * 1.8, entry_price * 0.025),
                        'tp2_price': entry_price * 1.10,
                        'shares': shares,
                        'status': 'OPEN',
                        'scaled_out': False,
                        'is_reentry': True,
                        'strategy_name': 'EMA 9/21 Yeniden Giriş',
                        'entry_score': float(sig.get('score', 0)),
                        'entry_checks': sig.get('_entry_checks', ''),
                        'atr_value': setup['atr_value'],
                        'risk_amount': risk_amount,
                        'market_regime': market_regime
                    })
                    stopped_out_symbols.remove(sym)

        # Seans sonu: acik pozisyonlari kapat.
        # Ancak BUGUN icin seans henuz 17:50'den onceyse canli modda acik birak;
        # frontend "Islemde" olarak gostersin.
        now = datetime.now()
        is_today = date_str == now.strftime("%Y-%m-%d")
        close_open_now = is_today and now.time() >= time(17, 50)

        for trade in [t for t in active_trades if t['status'] == 'OPEN']:
            sym = trade['symbol']
            df = dfs[sym]
            if not df.empty:
                last_time = df.index[-1]
                close = float(df.iloc[-1]['Close'])
                if close_open_now:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(last_time)
                    trade['exit_price'] = close
                    buy_volume = trade['shares'] * trade['entry_price']
                    sell_volume = trade['shares'] * close
                    commission = (buy_volume + sell_volume) * 0.0004
                    gross_pnl = trade['shares'] * (close - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl - commission
                    trade['pnl_pct'] = (trade['pnl_val'] / buy_volume) * 100
                    trade['exit_reason'] = "⏱️ SEANS SONU NAKİTE GEÇİŞ"
                else:
                    # Canli: acik pozisyon olarak kaydet, PnL gecici son fiyatla
                    trade['exit_time'] = None
                    trade['exit_price'] = None
                    buy_volume = trade['shares'] * trade['entry_price']
                    gross_pnl = trade['shares'] * (close - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl
                    trade['pnl_pct'] = (gross_pnl / buy_volume) * 100
                    trade['exit_reason'] = "🔓 AÇIK POZİSYON"
                completed_trades.append(trade)

        self._save_trades(date_str, completed_trades)
        print(f"[SimEngine] {date_str} için ÇELİK SİSTEM tamamlandı. İşlem Sayısı: {len(completed_trades)}")

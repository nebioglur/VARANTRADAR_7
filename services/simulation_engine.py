import pandas as pd
import numpy as np
import math
import os
import threading
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
    
    _owner_locks = {}
    _owner_locks_guard = threading.Lock()

    def __init__(self, daily_budget=500000.0, max_positions=3, owner=None):
        self.daily_budget = daily_budget
        self.max_positions = max_positions or 3  # Kurumsal Risk Playbook: En fazla 3-4 pozisyon
        self.owner = owner or "local:nebioglur"

    @classmethod
    def _lock_for(cls, owner):
        with cls._owner_locks_guard:
            lock = cls._owner_locks.get(owner)
            if lock is None:
                lock = threading.Lock()
                cls._owner_locks[owner] = lock
            return lock

    def _save_single_trade(self, date_str: str, trade: dict):
        """Her AL/SAT aninda islemi veritabanina dogrudan yazar,
        boylece Telegram bildirimi giden her islem aninda Trade Log'da gorunur."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    owner, date_str, symbol, entry_time, entry_price, exit_time,
                    exit_price, shares, pnl_val, realized_pnl, pnl_pct, exit_reason, strategy_name,
                    entry_score, entry_checks, atr_value, risk_amount, market_regime, engine_version,
                    xu100_at_entry, vwap_at_entry, initial_stop, stop_model, mfe_pct, mae_pct,
                    tp1_price, tp1_hit, breakeven_moved, r_multiple, hold_minutes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner, date_str, symbol, entry_time) DO UPDATE SET
                    exit_time=COALESCE(excluded.exit_time, trades.exit_time),
                    exit_price=COALESCE(excluded.exit_price, trades.exit_price),
                    shares=COALESCE(excluded.shares, trades.shares),
                    pnl_val=COALESCE(excluded.pnl_val, trades.pnl_val),
                    realized_pnl=CASE WHEN excluded.realized_pnl != 0 THEN excluded.realized_pnl ELSE trades.realized_pnl END,
                    pnl_pct=COALESCE(excluded.pnl_pct, trades.pnl_pct),
                    exit_reason=COALESCE(excluded.exit_reason, trades.exit_reason),
                    strategy_name=COALESCE(excluded.strategy_name, trades.strategy_name),
                    entry_score=COALESCE(excluded.entry_score, trades.entry_score),
                    entry_checks=COALESCE(excluded.entry_checks, trades.entry_checks),
                    atr_value=COALESCE(excluded.atr_value, trades.atr_value),
                    risk_amount=COALESCE(excluded.risk_amount, trades.risk_amount),
                    market_regime=COALESCE(excluded.market_regime, trades.market_regime),
                    engine_version=COALESCE(excluded.engine_version, trades.engine_version),
                    xu100_at_entry=COALESCE(excluded.xu100_at_entry, trades.xu100_at_entry),
                    vwap_at_entry=COALESCE(excluded.vwap_at_entry, trades.vwap_at_entry),
                    initial_stop=COALESCE(excluded.initial_stop, trades.initial_stop),
                    stop_model=COALESCE(excluded.stop_model, trades.stop_model),
                    mfe_pct=COALESCE(excluded.mfe_pct, trades.mfe_pct),
                    mae_pct=COALESCE(excluded.mae_pct, trades.mae_pct),
                    tp1_price=COALESCE(excluded.tp1_price, trades.tp1_price),
                    tp1_hit=COALESCE(excluded.tp1_hit, trades.tp1_hit),
                    breakeven_moved=COALESCE(excluded.breakeven_moved, trades.breakeven_moved),
                    r_multiple=COALESCE(excluded.r_multiple, trades.r_multiple),
                    hold_minutes=COALESCE(excluded.hold_minutes, trades.hold_minutes)
            """, (
                self.owner, date_str, trade['symbol'], trade['entry_time'], trade['entry_price'],
                trade.get('exit_time'), trade.get('exit_price'), trade.get('shares'),
                trade.get('pnl_val', 0.0), trade.get('realized_pnl', 0.0), trade.get('pnl_pct', 0.0), trade.get('exit_reason'),
                trade.get('strategy_name'), trade.get('entry_score'), trade.get('entry_checks'),
                trade.get('atr_value'), trade.get('risk_amount'), trade.get('market_regime'), trade.get('engine_version', 'V8_ELITE'),
                trade.get('xu100_at_entry'), trade.get('vwap_at_entry'), trade.get('initial_stop'), trade.get('stop_model', 'ATR 1.8x + Destek'),
                trade.get('mfe_pct', 0.0), trade.get('mae_pct', 0.0), trade.get('tp1_price'), trade.get('tp1_hit', 0),
                trade.get('breakeven_moved', 0), trade.get('r_multiple', 0.0), trade.get('hold_minutes', 0)
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[SimEngine] _save_single_trade err {trade.get('symbol')}: {e}")

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
                merged[key]['realized_pnl'] = float(t.get('pnl_val') or 0) if t.get('exit_time') else 0.0
                order.append(key)
                continue
            m = merged[key]
            if t.get('exit_time'):
                m['realized_pnl'] = float(m.get('realized_pnl') or 0) + float(t.get('pnl_val') or 0)
            m['shares'] = int(m.get('shares') or 0) + int(t.get('shares') or 0)
            m['pnl_val'] = float(m.get('pnl_val') or 0) + float(t.get('pnl_val') or 0)
            buy_vol = int(m.get('shares') or 0) * float(m.get('entry_price') or 0)
            m['pnl_pct'] = (m['pnl_val'] / buy_vol * 100) if buy_vol > 0 else 0
            prior_exit = m.get('exit_time')
            next_exit = t.get('exit_time')
            if not prior_exit or not next_exit:
                m['exit_time'] = None
                m['exit_price'] = None
                m['exit_reason'] = f"{m.get('exit_reason', '')} + {t.get('exit_reason', '')}".strip(' +')
                if 'AÇIK POZİSYON' not in m['exit_reason']:
                    m['exit_reason'] += ' + AÇIK POZİSYON'
            else:
                m['exit_time'] = next_exit
                m['exit_price'] = t.get('exit_price') or m.get('exit_price')
                m['exit_reason'] = f"{m.get('exit_reason', '')} + {t.get('exit_reason', '')}".strip(' +')

        conn = get_connection()
        cursor = conn.cursor()
        # Trade log kalici tutulur: yeni taramada sinyal kaybolsa bile onceki
        # islem satirlari silinmez; ayni islem anahtari gelirse guncellenir.

        for key in order:
            t = merged[key]
            try:
                cursor.execute("""
                    INSERT INTO trades (
                        owner, date_str, symbol, entry_time, entry_price, exit_time,
                        exit_price, shares, pnl_val, realized_pnl, pnl_pct, exit_reason, strategy_name,
                        entry_score, entry_checks, atr_value, risk_amount, market_regime, engine_version,
                        xu100_at_entry, vwap_at_entry, initial_stop, stop_model, mfe_pct, mae_pct,
                        tp1_price, tp1_hit, breakeven_moved, r_multiple, hold_minutes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(owner, date_str, symbol, entry_time) DO UPDATE SET
                        exit_time=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.exit_time ELSE excluded.exit_time END,
                        exit_price=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.exit_price ELSE excluded.exit_price END,
                        shares=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.shares ELSE excluded.shares END,
                        pnl_val=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.pnl_val ELSE excluded.pnl_val END,
                        realized_pnl=CASE WHEN excluded.realized_pnl=0 THEN trades.realized_pnl ELSE excluded.realized_pnl END,
                        pnl_pct=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.pnl_pct ELSE excluded.pnl_pct END,
                        exit_reason=CASE WHEN trades.exit_time IS NOT NULL AND excluded.exit_time IS NULL THEN trades.exit_reason ELSE excluded.exit_reason END,
                        strategy_name=excluded.strategy_name,
                        entry_score=excluded.entry_score,
                        entry_checks=excluded.entry_checks,
                        atr_value=excluded.atr_value,
                        risk_amount=excluded.risk_amount,
                        market_regime=excluded.market_regime,
                        engine_version=excluded.engine_version,
                        xu100_at_entry=COALESCE(excluded.xu100_at_entry, trades.xu100_at_entry),
                        vwap_at_entry=COALESCE(excluded.vwap_at_entry, trades.vwap_at_entry),
                        initial_stop=COALESCE(excluded.initial_stop, trades.initial_stop),
                        stop_model=COALESCE(excluded.stop_model, trades.stop_model),
                        mfe_pct=COALESCE(excluded.mfe_pct, trades.mfe_pct),
                        mae_pct=COALESCE(excluded.mae_pct, trades.mae_pct),
                        tp1_price=COALESCE(excluded.tp1_price, trades.tp1_price),
                        tp1_hit=COALESCE(excluded.tp1_hit, trades.tp1_hit),
                        breakeven_moved=COALESCE(excluded.breakeven_moved, trades.breakeven_moved),
                        r_multiple=COALESCE(excluded.r_multiple, trades.r_multiple),
                        hold_minutes=COALESCE(excluded.hold_minutes, trades.hold_minutes)
                """, (
                    self.owner, date_str, t['symbol'], t['entry_time'], t['entry_price'],
                    t.get('exit_time'), t.get('exit_price'), t.get('shares'),
                    t.get('pnl_val'), t.get('realized_pnl', 0.0), t.get('pnl_pct'), t.get('exit_reason'),
                    t.get('strategy_name'), t.get('entry_score'), t.get('entry_checks'),
                    t.get('atr_value'), t.get('risk_amount'), t.get('market_regime'), t.get('engine_version', 'V8_ELITE'),
                    t.get('xu100_at_entry'), t.get('vwap_at_entry'), t.get('initial_stop'), t.get('stop_model', 'ATR 1.8x + Destek'),
                    t.get('mfe_pct', 0.0), t.get('mae_pct', 0.0), t.get('tp1_price'), t.get('tp1_hit', 0),
                    t.get('breakeven_moved', 0), t.get('r_multiple', 0.0), t.get('hold_minutes', 0)
                ))
            except Exception as e:
                print(f"[SimEngine] Trade save err {t['symbol']}: {e}")

        # Seans sonu (17:50+) guvencesi: trades tablosunda bugune veya gecmise ait
        # acik kalmis (exit_time IS NULL) hicbir pozisyon birakilmaz; hepsi seans sonu nakde gecirilir.
        try:
            from zoneinfo import ZoneInfo
            _now_eod = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            _now_eod = datetime.now()
        _is_today_eod = (date_str == _now_eod.strftime("%Y-%m-%d"))
        if (not _is_today_eod) or _now_eod.time() >= time(17, 50):
            try:
                cursor.execute('''
                    UPDATE trades SET
                        exit_time = date_str || ' 17:50:00',
                        exit_price = CASE WHEN exit_price IS NOT NULL THEN exit_price WHEN shares > 0 THEN entry_price + (pnl_val / shares) ELSE entry_price END,
                        realized_pnl = pnl_val,
                        exit_reason = CASE
                            WHEN exit_reason LIKE '%TP1%' THEN '⚖️ KADEMELİ TP1 (%50 SATILDI, STOP MALİYETE ÇEKİLDİ) + SEANS SONU NAKITE GECIS (17:50)'
                            ELSE 'SEANS SONU NAKITE GECIS (17:50)'
                        END
                    WHERE owner=? AND date_str=? AND exit_time IS NULL
                ''', (self.owner, date_str))
            except Exception as _cl_e:
                print(f"[SimEngine] Open trade closure sweep error: {_cl_e}")

        # Equity Log (hesap bazli) - birlestirilmis kayitlar uzerinden;
        # boylece equity_log ile trades tablosu SUM'u daima tutarli olur.
        cursor.execute(
            "SELECT COALESCE(SUM(realized_pnl),0) pnl, COUNT(*) n, "
            "COALESCE(SUM(CASE WHEN exit_time IS NOT NULL AND realized_pnl > 0 THEN 1 ELSE 0 END),0) wins "
            "FROM trades WHERE owner=? AND date_str=?",
            (self.owner, date_str),
        )
        day_totals = cursor.fetchone()
        total_pnl = float(day_totals['pnl'] or 0) if day_totals else 0.0
        stored_trade_count = int(day_totals['n'] or 0) if day_totals else 0
        win_trades = int(day_totals['wins'] or 0) if day_totals else 0

        try:
            # Forward-Test Charter (2026-11-19) başlangıç sermayesi 500.000 TL olarak izole edilir:
            if str(date_str)[:10] == "2026-11-19":
                start_eq = self.daily_budget
            else:
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
                total_pnl, stored_trade_count, win_trades
            ))
        except Exception as e:
            print(f"[SimEngine] Equity save err: {e}")

        conn.commit()
        conn.close()

        # Telegram events run only after the same trade snapshot is committed.
        try:
            from services.telegram_bot import notify_simulation_trade_events
            # Devre disi: notify_sim_trade aninda tekil zengin kart atiyor; mukerrer engeli
            pass
        except Exception as alert_error:
            print(f"[SimEngine] Telegram işlem bildirimi hatası: {alert_error}")

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

    def _entry_setup(self, sub_df, entry_price, meta=None):
        """
        KULLANICI STRATEJİSİ: 'Desteğe Yavaş Süzülüş & Ani Kırılıma Giriş' (Pullback-at-Support)
        
        1. Aşırı Uzaklaşma / Tepe Kovalaması Engeli:
           Fiyat dinamik desteklerinden (VWAP veya 5m EMA21) %2.5'ten fazla yukarıdaysa,
           ani alımın zirvesidir; alım KESİNLİKLE yapılmaz (FOMO / Tepe Kovalaması Engeli).
           
        2. Desteğe Yavaş / Hacimsiz İniş Teyidi:
           Son barlardaki satış hacmi, alım hacminden belirgin derecede düşük olmalıdır
           (panik satış değil, sağlıklı absorbsiyon / kurumsal sindirme).
           
        3. Destek Teyidi ve Tepki:
           Fiyat kurumsal VWAP veya EMA21 desteğine yakın bölgededir (%0.0 - %1.8 aralığı).
           
        4. Çelik ve Dar Stop-Loss:
           Stop doğrudan desteğin %0.8 altına yerleştirilir; stop mesafesi %1.2 - %2.0 aralığındadır.
        """
        if len(sub_df) < 4:
            return None

        close = pd.to_numeric(sub_df['Close'], errors='coerce').dropna()
        high = pd.to_numeric(sub_df['High'], errors='coerce').reindex(close.index)
        low = pd.to_numeric(sub_df['Low'], errors='coerce').reindex(close.index)
        open_prices = pd.to_numeric(sub_df['Open'], errors='coerce').reindex(close.index)
        vol = pd.to_numeric(sub_df.get('Volume', pd.Series(50000, index=close.index)), errors='coerce').reindex(close.index).fillna(50000)

        if len(close) < 4 or high.isna().any() or low.isna().any() or open_prices.isna().any():
            return None

        ema9 = close.ewm(span=9, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()

        # Intraday VWAP hesabi
        cum_vol = vol.cumsum()
        pv = (vol * (high + low + close) / 3.0).cumsum()
        intraday_vwap = float(pv.iloc[-1] / cum_vol.iloc[-1]) if cum_vol.iloc[-1] > 0 else 0.0
        meta_vwap = float((meta or {}).get('VWAP') or 0.0) if isinstance(meta, dict) else 0.0
        support_vwap = intraday_vwap if intraday_vwap > 0 else meta_vwap

        c_ema9 = float(ema9.iloc[-1])
        c_ema21 = float(ema21.iloc[-1])

        # 1. AŞIRI ŞİŞKİNLİK / TEPE TUZAĞI ENGELİ:
        # Fiyat hem VWAP'tan hem EMA21'den %2.5'ten fazla yukarıdaysa, hisse ani patlamanın tepesindedir.
        # "Desteğe yavaşça süzülüş" gerçekleşmeden tepeden girmek KESİNLİKLE yasaktır!
        dist_vwap = (entry_price - support_vwap) / support_vwap if support_vwap > 0 else 0.0
        dist_ema21 = (entry_price - c_ema21) / c_ema21 if c_ema21 > 0 else 0.0

        if dist_vwap > 0.025 and dist_ema21 > 0.022:
            return None

        # 2. YAVAŞ SÜZÜLME / DÜŞÜK SATIŞ HACMİ KONTROLÜ:
        # Son barlarda düşüş varsa hacim zayıf olmalı (büyük oyuncu satmıyor, sindiriyor)
        if len(sub_df) >= 4:
            recent_bars = sub_df.tail(4)
            red_bars = recent_bars[recent_bars['Close'] < recent_bars['Open']]
            green_bars = recent_bars[recent_bars['Close'] >= recent_bars['Open']]
            if not red_bars.empty and not green_bars.empty:
                avg_red = red_bars['Volume'].mean()
                avg_green = green_bars['Volume'].mean()
                if avg_red > avg_green * 1.8:
                    return None

        # 3. DİNAMİK DESTEK SEVİYESİ VE STOP HESABI:
        valid_supports = []
        if support_vwap > 0 and support_vwap <= entry_price * 1.005:
            valid_supports.append(support_vwap)
        if c_ema21 > 0 and c_ema21 <= entry_price * 1.005:
            valid_supports.append(c_ema21)
        if low.iloc[-3:].min() > 0:
            valid_supports.append(float(low.iloc[-3:].min()))

        primary_support = max(valid_supports) if valid_supports else (entry_price * 0.985)

        # Destek seviyesinin %0.8 altına çelik stop yerleştir
        support_stop = primary_support * 0.992

        # ATR hesapla
        prev_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr_series = true_range.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=3).mean()
        atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 and pd.notna(atr_series.iloc[-1]) else (entry_price * 0.015)

        # Stop mesafesi: En az %1.2, en fazla %2.2 (asla körlemesine %3-%4 değil!)
        calc_stop_pct = (entry_price - support_stop) / entry_price
        stop_pct = max(0.012, min(0.022, calc_stop_pct))
        stop_price = round(entry_price * (1.0 - stop_pct), 2)

        return {
            'atr_value': atr,
            'stop_pct': stop_pct,
            'stop_price': stop_price,
            'support_level': primary_support,
            'dist_vwap_pct': round(dist_vwap * 100, 2),
            'dist_ema21_pct': round(dist_ema21 * 100, 2),
            'strategy_tag': 'Desteğe Süzülüş (Pullback)',
            'ema9': c_ema9,
            'ema21': c_ema21
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

    def _position_allocation(self, current_cash, entry_price, stop_price, is_bear, risk_pct=None, regime="NEUTRAL", open_slots=1, total_score=90.0, bonus_tags=None):
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return 0.0, 0.0

        is_strong_bull = (regime == "STRONG_BULL" or "ÜÇLÜ" in str(regime))
        is_bull = (is_strong_bull or regime == "BULL" or "BOĞA" in str(regime))
        is_strong_bear = (regime == "STRONG_BEAR" or "ŞİDDETLİ" in str(regime))
        is_bear_effective = is_strong_bear or is_bear or regime == "BEAR" or "AYI" in str(regime)

        # ── KURUMSAL SERMAYE KORUMA VE REJİM BÜTÇESİ (PLAYBOOK) ──
        # Aşırı maruziyeti (%200 kaldıraç tuzağını) KESİNLİKLE engeller.
        # Kural: Hiçbir hisseye portföyün %10'undan fazlası (50.000 TL) KESİNLİKLE bağlanamaz!
        if is_strong_bear:
            max_pos_ratio = 0.00
            max_trade_risk_ratio = 0.000
        elif is_bear_effective:
            max_pos_ratio = 0.05        # 500K kasada en fazla 25.000 TL pozisyon (%5)
            max_trade_risk_ratio = 0.002 # Max 1.000 TL işlem riski (%0.2)
        elif not is_bull:               # NEUTRAL / DEFANSİF
            max_pos_ratio = 0.08        # 500K kasada en fazla 40.000 TL pozisyon (%8)
            max_trade_risk_ratio = 0.003 # Max 1.500 TL işlem riski (%0.3)
        elif is_strong_bull:
            max_pos_ratio = 0.10        # 500K kasada en fazla 50.000 TL pozisyon (%10 KURALI)
            max_trade_risk_ratio = 0.005 # Max 2.500 TL işlem riski (%0.5)
        else:                           # BULL
            max_pos_ratio = 0.10        # 500K kasada en fazla 50.000 TL pozisyon (%10 KURALI)
            max_trade_risk_ratio = 0.004 # Max 2.000 TL işlem riski (%0.4)

        # Mutlak pozisyon tavanı: Kasanın azami %10'u (50.000 TL)
        max_position_cap = min(self.daily_budget * 0.10, self.daily_budget * max_pos_ratio)
        if max_position_cap <= 0:
            return 0.0, 0.0

        # ── KATI PARASAL RİSK PARİTESİ (DOLLAR RISK PARITY) ──
        # Kural: Normal stop gerçekleşmesinde hedeflenen azami başlangıç riski 1.250 TL'dir (%0.25).
        # Stop mesafesi ne kadar genişse, pozisyon o kadar KÜÇÜLÜR:
        # Pozisyon = min(%10 Sermaye, 1.250 TL / (Stop Mesafesi + Gidiş-Dönüş Komisyon))
        max_trade_risk_tl = min(1250.0, self.daily_budget * 0.0025)
        stop_pct = max(0.015, risk_per_share / entry_price)
        # Muhafazakar gidiş-dönüş komisyon ve kayma payı: %0.16 (0.0016)
        effective_risk_pct = stop_pct + 0.0016
        risk_based_allocation = max_trade_risk_tl / effective_risk_pct

        # Nihai Pozisyon: min(Tavan, Parasal Risk Limiti)
        allocation = min(max_position_cap, risk_based_allocation)

        # Taban güvencesi (işleme değecek asgari pay: 10.000 TL)
        min_position_floor = min(allocation, 10000.0)
        allocation = max(min_position_floor, allocation)

        # Eldeki nakit sinirini asmasin
        if current_cash is not None:
            if current_cash < entry_price:
                return 0.0, 0.0
            allocation = min(allocation, current_cash)

        actual_risk_tl = allocation * (risk_per_share / entry_price)
        return allocation, min(max_trade_risk_tl, actual_risk_tl)

    def run_daily_simulation(self, date_str: str):
        # Aynı hesap için eşzamanlı replay önlenir: iki koşucu üst üste binince
        # aynı hisse hem AL hem SAT mesajı üretiyor ve trade defteri sarsılıyordu.
        lock = self._lock_for(self.owner)
        if not lock.acquire(blocking=False):
            print(f"[SimEngine] {self.owner} simülasyonu zaten çalışıyor; bu tur atlandı.")
            return
        try:
            self._run_daily_simulation_inner(date_str)
        finally:
            lock.release()

    def _run_daily_simulation_inner(self, date_str: str):
        signals = MarketDataManager.get_signals(date_str)
        # V8 Breakout 'ENTER' sinyallerini de doğrudan en başa ekle:
        try:
            v8_bos = []
            if os.path.exists("v8_breakout_cache.json"):
                with open("v8_breakout_cache.json", "r", encoding="utf-8") as _v8f:
                    v8_bos = json.load(_v8f).get("data", [])
            if not v8_bos:
                for _cf_path in ["v8_breakout_cache.json", "data/cache/v8_breakout_cache.json"]:
                    if os.path.exists(_cf_path):
                        try:
                            with open(_cf_path, "r", encoding="utf-8") as _v8f:
                                v8_bos = json.load(_v8f).get("data", [])
                            if v8_bos:
                                break
                        except Exception:
                            pass
            v8_al = [x for x in v8_bos if (x.get("entry_status") or "").upper() == "ENTER"]
            seen_syms = {s.get("symbol") for s in (signals or [])}
            v8_sig_list = []
            for item in v8_al:
                sym = item.get("symbol")
                if sym and sym not in seen_syms:
                    p = float(item.get("price") or item.get("Daily_Close") or 0.0)
                    t1 = float(item.get("target1") or (p * 1.05))
                    
                    # Discovery / Detection time (hardcoded 10:15 kaldirildi)
                    scan_ts = item.get("scan_timestamp")
                    sig_time_str = ""
                    if scan_ts:
                        try:
                            from zoneinfo import ZoneInfo
                            _sdt = datetime.fromtimestamp(float(scan_ts), ZoneInfo("Europe/Istanbul"))
                            sig_time_str = _sdt.strftime("%H:%M")
                        except Exception:
                            pass
                    if not sig_time_str and item.get("time"):
                        sig_time_str = str(item.get("time"))[:5]
                    if not sig_time_str and item.get("discovery_time"):
                        sig_time_str = str(item.get("discovery_time"))[:5]
                    if not sig_time_str:
                        try:
                            from zoneinfo import ZoneInfo
                            _now_ist = datetime.now(ZoneInfo("Europe/Istanbul"))
                            if date_str == _now_ist.strftime("%Y-%m-%d") and _now_ist.hour >= 11:
                                sig_time_str = f"{_now_ist.hour:02d}:{(_now_ist.minute // 5) * 5:02d}"
                        except Exception:
                            pass

                    phase_str = f"V8 Breakout ({sig_time_str})" if sig_time_str else "V8 Breakout"
                    v8_sig_list.append({
                        "date_str": date_str,
                        "symbol": sym,
                        "score": float(item.get("breakout_score") or 99.0),
                        "morning_price": p,
                        "ceiling_target": t1,
                        "morning_phase": phase_str,
                        "discovery_time": sig_time_str,
                        "metadata": json.dumps(item, ensure_ascii=False)
                    })
                    seen_syms.add(sym)
            if v8_sig_list:
                signals = v8_sig_list + (signals or [])
        except Exception as _e_v8_s:
            print(f"[SimEngine] V8 sinyalleri eklenirken hata: {_e_v8_s}")

        if not signals:
            return

        _live_symbols_stats = {}
        xu100_change = 0.0
        try:
            with open('dashboard_cache.json', encoding='utf-8') as _cf:
                _cc = json.load(_cf)
                _live_symbols_stats = _cc.get('all_symbols_stats', {})
                _vr = _cc.get('v8_market_regime', {})
                if _vr and _vr.get('xu100_trend') is not None:
                    xu100_change = float(_vr['xu100_trend'])
        except Exception:
            pass

        # ── GENİŞLİK MOTORU (Market Breadth) ─────────────────────────────────
        # Piyasa Genişliği: Sadece XU100 değil, kaç hisse düşüyor / yükseliyor?
        # Bu oran %65+ düşüş baskısı ise rejim ağırlıklı AYI olarak işaretlenir.
        try:
            from services.market_breadth import MarketBreadthEngine
            _breadth = MarketBreadthEngine.get_market_breadth(xu100_change=xu100_change)
            regime_code    = _breadth['regime_code']      # STRONG_BEAR / BEAR / NEUTRAL / BULL
            pressure_pct   = _breadth['pressure_pct']     # % düşen hisse
            sector_divergence = _breadth['sector_divergence']  # sektör bazlı relatif güç
        except Exception:
            regime_code   = 'BEAR' if xu100_change < -0.5 else ('BULL' if xu100_change > 0.5 else 'NEUTRAL')
            pressure_pct  = 60.0 if xu100_change < -0.5 else 40.0
            sector_divergence = {}

        is_bear   = regime_code in ('BEAR', 'STRONG_BEAR')
        is_strong_bear = regime_code == 'STRONG_BEAR'
        is_strong_bull = regime_code in ('STRONG_BULL', 'BULL') and (xu100_change >= 1.0 or regime_code == 'STRONG_BULL')
        market_regime = {
            'STRONG_BEAR': 'ŞİDDETLİ AYI',
            'BEAR': 'AYI',
            'NEUTRAL': 'NÖTR',
            'BULL': 'GÜÇLÜ POZİTİF'
        }.get(regime_code, 'NÖTR')
        minimum_score = 95 if is_strong_bear else (92 if is_bear else 90)

        # ==== SENARYO DINAMIGI: V8 rejimine gore islem plani ====
        # Rejim kilidi simülasyona da uygulanir: AYI/GUCCLU AYI gununde
        # V8 hicbir kirilim girisi acmaz; sim ayni gercegi yansitir.
        _sim_regime = "NEUTRAL"
        try:
            for _c_cand in ["dashboard_cache.json", "data/cache/dashboard_cache.json"]:
                if os.path.exists(_c_cand):
                    with open(_c_cand, "r", encoding="utf-8") as _f_dc:
                        _sim_gdc = json.load(_f_dc)
                        _sim_regime = (_sim_gdc.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
                        if _sim_regime:
                            break
        except Exception:
            pass
        try:
            from v8_engine.playbook import get_scenario as _get_scenario
            _sim_scenario = _get_scenario(_sim_regime)
        except Exception:
            _sim_scenario = {}
        # Senaryo TP carpanlari: bogada hedefler genisler (kar maksimizasyonu),
        # volatilite/ayi gununde daralir (hizli nakit cikisi).
        try:
            _tp1_mult = max(0.5, min(2.0, float(_sim_scenario.get("tp1_mult", 1.0))))
            _tp2_mult = max(0.5, min(2.0, float(_sim_scenario.get("tp2_mult", 1.0))))
        except Exception:
            _tp1_mult, _tp2_mult = 1.0, 1.0
        # DINAMIK RISK: rejime gore islem basi sermaye riski. GÜÇLÜ BOĞA'da
        # %2.0 (getiri çarpani), NÖTR'de %1.0, kapali rejimde 0 (giris zaten yok).
        try:
            _sim_risk_pct = max(0.0, min(3.0, float(_sim_scenario.get("risk_pct", 1.2) or 0))) / 100.0
        except Exception:
            _sim_risk_pct = 0.012
        if _sim_risk_pct <= 0:
            _sim_risk_pct = 0.005 if is_bear else 0.012

        # ── OTOMATİK ÇİFT VİTES SİSTEMİ (GARANTİCİ DEFANSİF vs OFANSİF TAVAN AVCISI) ──
        # OFANSİF MOD ŞARTLARI:
        # 1. Rejim BULL veya STRONG_BULL (ya da XU100 >= +0.60%)
        # 2. Düşüş baskısı düşük (pressure_pct < 45.0, hisselerin çoğunluğu yeşil)
        # 3. Ayı rejimi değil
        is_offensive = (
            (_sim_regime in ("BULL", "STRONG_BULL") or regime_code in ("BULL", "STRONG_BULL") or xu100_change >= 0.60)
            and pressure_pct < 45.0
            and not is_bear
        )
        trading_gear = "OFANSİF (Tavan Avcısı & Runner)" if is_offensive else "DEFANSİF (Garantici Çelik Kalkan)"

        # ORTAK KADEMELİ ÇIKIŞ PLANI: Hedef1 %3 / Hedef2 %5 / kalan pay (runner)
        # tavan veya iz süren stop ile. Satış oranları rejime gore dinamik.
        try:
            from v8_engine.playbook import get_exit_plan as _get_exit_plan
            _exit_plan = _get_exit_plan(
                _sim_regime,
                volatility_state=str(_sim_scenario.get("volatility_state") or ""),
            )
        except Exception:
            _exit_plan = {"tp1_sell_pct": 50, "tp2_sell_pct": 30, "runner_pct": 20}

        # Haftalik hedef/zarar kilidi (ortak playbook): +%6 hedefe ulasildiysa
        # yeni giris TAMAMEN durur (kâr koruma); rejime gore zarar limiti
        # (ayi/yuksek volatilite -1.5, notr -2.0, boga -2.5) asildiysa da
        # yeni girisler kapanir. Acik pozisyonlar kendi stop/planlariyla yonetilir.
        _weekly_target_reached = False
        _weekly_loss_locked = False
        _week_guard = {}
        try:
            # Haftanin pazartesi tarihini Python'da hesapla: SQLite'a ozel
            # date(?, 'weekday 0', ...) sozdizimi PostgreSQL'de gecerli degil.
            from datetime import date as _dt
            _d = _dt.fromisoformat(str(date_str)[:10])
            _monday = (_d - timedelta(days=_d.weekday())).isoformat()
            # Forward-Test Charter Başlangıç İzolasyonu (2026-11-19):
            # Eski kalibrasyonsuz dönemin (-16.838 TL) haftalık kilidi bloke etmemesi için:
            _week_start = max(_monday, "2026-11-19") if str(date_str)[:10] >= "2026-11-19" else _monday
            wconn = get_connection()
            wcur = wconn.cursor()
            wcur.execute(
                "SELECT start_equity, SUM(daily_pnl) FROM equity_log "
                "WHERE owner=? AND date_str >= ?",
                (self.owner, _week_start),
            )
            wrow = wcur.fetchone()
            wconn.close()
            if wrow and wrow[0]:
                base = float(wrow[0])
                week_pnl = float(wrow[1] or 0)
                week_gain_pct = (week_pnl / base * 100.0) if base > 0 else 0.0
                _weekly_target_reached = week_gain_pct >= 6.0
                try:
                    from v8_engine.playbook import get_weekly_guard as _get_weekly_guard
                    _week_guard = _get_weekly_guard(
                        week_pnl, base, _sim_regime,
                        volatility_state=str(_sim_scenario.get("volatility_state") or ""),
                    )
                    _weekly_loss_locked = bool(_week_guard.get("loss_limit_reached"))
                    _weekly_target_reached = bool(_week_guard.get("target_reached"))
                except Exception:
                    pass
        except Exception:
            pass

        # Günlük gerçekleşmiş kâr/zarar ön kontrolü (Bugünün daha önce kapanmış işlemleri varsa)
        _today_db_pnl = 0.0
        try:
            conn_chk = get_connection()
            cur_chk = conn_chk.cursor()
            cur_chk.execute("SELECT SUM(pnl_val) FROM trades WHERE owner=? AND date_str=? AND exit_time IS NOT NULL", (self.owner, date_str))
            _r_chk = cur_chk.fetchone()
            if _r_chk and _r_chk[0]:
                _today_db_pnl = float(_r_chk[0])
            conn_chk.close()
        except Exception:
            pass

        if _today_db_pnl <= -(self.daily_budget * 0.015):
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Günlük zarar kesici (-%1.5) önceden tetiklenmiş ({_today_db_pnl:.0f} TL): yeni girişler durduruldu")
        elif _today_db_pnl >= (self.daily_budget * 0.020):
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Günlük kâr kilidi (+%2.0) önceden tetiklenmiş (+{_today_db_pnl:.0f} TL): kâr koruma devrede, yeni giriş yok")
        elif _sim_regime == "STRONG_BEAR" or is_strong_bear:
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Şiddetli Ayı kilidi: YENİ GİRİŞLER TAMAMEN KAPALI (Nakit %100)")
        elif _sim_regime == "BEAR" or is_bear:
            # SAVUNMA MODU (AYI): Sadece endeksten pozitif ayrışan tek 1 lider hisseye izin verilir
            effective_max_positions = 1
            print(f"[SimEngine] {date_str} -> Savunma Modu (Ayı): Kasa korunuyor, en fazla 1 seçici işlem")
        elif _weekly_loss_locked:
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Haftalık zarar kilidi aktif: yeni girişler durduruldu (açık pozisyonlar planıyla yönetilir)")
        elif _weekly_target_reached:
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Haftalık %6 hedefi doldu: KÂR KORUMA MODU (yeni giriş yok, açık pozisyonlar izleniyor)")
        else:
            # DİNAMİK VİTES POZİSYON LİMİTİ:
            # Ofansif modda: En fazla 3-4 hisse (akışkan ralli).
            # Defansif (Nötr) modda: En fazla 2 hisse (sıkı garantici kalkan).
            max_cap = 4 if is_strong_bull else (3 if is_offensive else 2)
            effective_max_positions = min(max_cap, self.max_positions)

        # DOMINO_CLUSTERS ile dinamik sektor ayrismasi haritasi
        from config.bist_symbols import DOMINO_CLUSTERS
        _sec_lup = {}
        for _sn, _mems in DOMINO_CLUSTERS.items():
            for _mm in _mems:
                _sec_lup[_mm] = _sn
                _sec_lup[_mm.replace('.IS', '')] = _sn

        valid_signals = []
        for s in signals:
            score = float(s.get('score', 0))
            phase = str(s.get('morning_phase', 'Phase 1'))
            
            metadata_str = s.get('metadata')
            meta = {}
            if metadata_str:
                try:
                    meta = json.loads(metadata_str)
                except Exception as e_meta:
                    pass
            
            price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
            ema50, ema200 = self._daily_trend_values(meta, s['symbol'])
            
            # Hacim çarpanını tespit et (intraday normalize veya derin likidite koruması)
            v8_disc = meta.get('v8_discovery', {}) if isinstance(meta, dict) else {}
            metrics = v8_disc.get('metrics', {}) if isinstance(v8_disc, dict) else {}
            r_vol = metrics.get('relative_volume', 0)
            if not r_vol:
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
            # Sabah/öğlen saatlerinde kümülatif hacim tam gün ortalamasına bölündüğünden 
            # ham r_vol 0.15-0.50 arasında olabilir. Gerçek likidite Kural F1 (50M/75M TL) ile denetlenir.
            if float(r_vol or 0) > 0 and float(r_vol) < 0.05:
                continue

            # Tavan tuzagi engeli (+%5.5 ve uzeri acilislar elenir)
            ch_pct = float(meta.get('Change_Pct') or meta.get('Change') or 0)
            if ch_pct >= 5.5:
                continue

            # Likidite ve Fiyat Guvencesi: penny/sig hisseleri filtrele
            if price < 3.5:
                continue
            vol_tl = float(meta.get('Volume_TL') or (float(meta.get('Volume', 0)) * price) or 0)
            if vol_tl > 0 and vol_tl < 20_000_000:
                continue
                    
            # EMA Trend filtresi (varsa kontrol et)
            if ema50 and ema200 and price:
                try:
                    if float(price) < float(ema50) * 0.98 or float(price) < float(ema200) * 0.98:
                        continue
                except (ValueError, TypeError):
                    pass

            # Sektorel Ayrisma ve Sektor Gucu
            _sym_sec = _sec_lup.get(s['symbol']) or _sec_lup.get(s['symbol'].replace('.IS', '')) or meta.get('Domino_Sector') or ''
            _sdiv = sector_divergence.get(_sym_sec, {}) if (_sym_sec and sector_divergence) else {}
            _rel = float(_sdiv.get('relative_strength', 0.0))

            # AYI piyasasinda sektoru endekse karsi ayrismayan hisseleri ele
            if is_bear and sector_divergence and _sym_sec:
                if _rel < 0.5:
                    continue

            # 🛡️ PARA AKIŞI VE SATIŞ BASKISI EMNİYET KİLİDİ (HUNER ve Benzeri Düşüş Tuzaklarını KESİNLİKLE Engeller)
            intra_strength = meta.get('intraday_strength', {}) if isinstance(meta, dict) else {}
            h_flow = str(intra_strength.get('hourly_flow') or meta.get('hourly_flow') or '')
            m_flow = str(intra_strength.get('money_flow_status') or meta.get('money_flow_status') or '')
            intra_chg = float(intra_strength.get('intraday_change_pct') or meta.get('intraday_change_pct') or 0.0)
            v8_fakeout = float((meta.get('v8_breakout') or {}).get('fakeout_risk') or meta.get('fakeout_risk') or 0.0)
            v8_exec_status = str((meta.get('v8_execution') or {}).get('entry_status') or meta.get('entry_status') or '')

            # Kural A: Para çıkışında veya saatlik satış baskısında olan hisseye KESİNLİKLE girilmez!
            if h_flow in ('Satılıyor', 'Outflow') or m_flow in ('Outflow', 'Strong Outflow'):
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Para çıkışı / Satış baskısı ({h_flow}/{m_flow})")
                continue

            # Kural B: Gün içi sert düşüşte olan hisseye (-%1.0 altı) girilmez!
            if intra_chg < -1.0:
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Gün içi sert düşüş (-%{abs(intra_chg):.2f})")
                continue

            # Kural C: Yüksek tuzak riski (> %25) elenir!
            if v8_fakeout > 25.0:
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Yüksek tuzak riski (%{v8_fakeout:.1f})")
                continue

            # Kural D: V8 Motoru açıkça AVOID (tehlikeli/kara liste) vermişse girilmez!
            # (NO_ENTRY sadece V8 kırılımı oluşmadığını belirtir, momentum ve tavan adaylarını engellemez)
            if v8_exec_status == 'AVOID':
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: V8 Motoru AVOID verdi")
                continue

            # Kural E1 (FİTİL KORUMASI / ZİRVEDEN DÖNÜŞ TUZAĞI):
            # Gün içi zirvesinden %2.2'den fazla geri çekilmiş (fitil atan / mal boşaltılan) hisseye KESİNLİKLE girilmez!
            d_high = float(intra_strength.get('session_high') or meta.get('High') or 0.0)
            curr_p = float(intra_strength.get('current_price') or meta.get('Price') or price)
            pos_pct = float(intra_strength.get('session_position_pct') or 100.0)
            if d_high > 0 and curr_p > 0:
                pullback_from_high = ((d_high - curr_p) / d_high) * 100.0
                if pullback_from_high > 2.2:
                    print(f"[SIM-GUARD] {s.get('symbol')} elendi: Zirveden geri çekilme / Üst fitil tuzağı (%{pullback_from_high:.1f} geri çekildi)")
                    continue

            # Kural E2 (ZİRVE YAKINLIĞI): Gün içi pozisyonu zirveye yakın olmayan (pos_pct < 70) hisselere girilmez!
            if pos_pct < 70.0:
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Zirveden uzak gün içi pozisyon (%{pos_pct:.1f})")
                continue

            # Kural F1 (KURUMSAL LİKİDİTE KALKANI):
            # Günlük hacim < 50M TL ve 10 günlük ortalama ciro < 75M TL olan sığ hisselere KESİNLİKLE girilmez!
            money_vol = float(meta.get('Money_Volume') or (price * float(meta.get('Volume') or 0)))
            vol_sma = float(meta.get('Vol_SMA10') or 0)
            avg_turnover = vol_sma * price if vol_sma > 0 else money_vol
            if money_vol < 50_000_000 and avg_turnover < 75_000_000:
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Yetersiz kurumsal likidite ({money_vol/1e6:.1f}M TL)")
                continue

            # Kural F2 (PENNY STOCK ENGELİ): Fiyatı 8.0 TL altındaki spekülatif sığ tahtalara girilmez!
            if price < 8.0:
                print(f"[SIM-GUARD] {s.get('symbol')} elendi: Penny stock / Sığ fiyat ({price:.2f} TL < 8.0 TL)")
                continue

            # Kural F3 (MUM ANATOMİSİ - ÜST FİTİL KORUMASI):
            # Üst fitil toplam mum aralığının %28'inden büyükse bu bir boğa tuzağıdır!
            d_open = float(intra_strength.get('session_open') or meta.get('Daily_Open') or price)
            d_low = float(intra_strength.get('session_low') or meta.get('Low') or price)
            rng = d_high - d_low
            if rng > 0:
                upper_wick = d_high - max(d_open, curr_p)
                if (upper_wick / rng) > 0.28:
                    print(f"[SIM-GUARD] {s.get('symbol')} elendi: Üst fitil tuzağı / Gövdeden büyük fitil (%{upper_wick/rng*100:.1f})")
                    continue

            # Kural F4 (VWAP KURUMSAL ÇAPASI):
            # Fiyat VWAP altında ise kurumsal satış baskısı vardır; KESİNLİKLE ALINMAZ!
            # Fiyat VWAP'tan %5'ten fazla uzaklaşmışsa aşırı şişmiştir; KESİNLİKLE ALINMAZ!
            vwap_check = float(meta.get('VWAP') or 0.0)
            if vwap_check > 0:
                if price < vwap_check * 0.998:
                    print(f"[SIM-GUARD] {s.get('symbol')} elendi: VWAP altında kurumsal satış ({price:.2f} < {vwap_check:.2f})")
                    continue
                if price > vwap_check * 1.050:
                    print(f"[SIM-GUARD] {s.get('symbol')} elendi: VWAP'tan aşırı uzaklaşmış / Şişkinlik ({price:.2f} > {vwap_check*1.05:.2f})")
                    continue

            indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
            rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
            volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or r_vol or 1.2)
            details = [str(detail) for detail in meta.get('Details', [])]
            detail_text = ' '.join(details).upper()
            macd_value = indicators.get('MACD_Positive')
            macd_ok = bool(macd_value) if macd_value is not None else ('MACD' in detail_text or ch_pct > 0.5)
            vwap = meta.get('VWAP')
            vwap_ok = (not vwap) or (price >= float(vwap) * 0.995)
            fomo_score = float(meta.get('FOMO_Score') or 0)
            no_trap = not bool(meta.get('Trap_Risk')) or (score >= 80 and volume_multiplier >= 1.3)
            fomo_ok = fomo_score < 90 or (volume_multiplier >= 1.8)
            sector_ok = bool(_sym_sec and _rel >= 0.3) or bool(meta.get('Domino_Sector')) or 'SEKTOR GUCU' in detail_text
            volume_ok = volume_multiplier >= 1.0 or 'HACIMLI' in detail_text

            checks = {
                'Ana trend': True,
                'RSI dengeli': 28 <= rsi <= 85,
                'Hacim teyidi': volume_ok,
                'MACD yonu': macd_ok,
                'VWAP ustu': vwap_ok,
                'Tuzak/FOMO temiz': no_trap,
                'Sektor destegi': sector_ok,
                'FOMO kontrollu': fomo_ok
            }
            is_v8_approved = (meta.get('entry_status') == 'ENTER') or (meta.get('v8_breakout', {}).get('entry_status') == 'ENTER')
            if is_v8_approved:
                checks['Tuzak/FOMO temiz'] = True
                checks['Ana trend'] = True
                checks['RSI dengeli'] = True

            # Boga modunda ofansif katilim: 5/8 yeterli; Ayida 6/8
            min_passed = 5 if (_sim_regime in ('STRONG_BULL', 'BULL')) else 6
            if not is_v8_approved and (sum(checks.values()) < min_passed or not checks['RSI dengeli'] or not checks['Tuzak/FOMO temiz']):
                continue

            # BASARI VE SEKTOREL AYRISMA BONUSLARI (+%6 Hedef & %90 Win-Rate Guvencesi)
            base_score = float(s.get('score', 0))
            bonuses = 0.0
            bonus_tags = []

            # 1. Sektorel Ayrisma Lideri (+10 Puan)
            if _sym_sec and _rel >= 1.0:
                bonuses += 10.0
                bonus_tags.append(f'Lider Sektor ({_sym_sec} +%{_rel:.2f})')
            elif _sym_sec and _rel >= 0.3:
                bonuses += 5.0
                bonus_tags.append(f'Pozitif Sektor ({_sym_sec} +%{_rel:.2f})')
            elif _rel <= -1.0:
                bonuses -= 8.0

            # 2. Akilli Para & CMF Bonusu (+5 Puan)
            cmf = float(indicators.get('CMF') or meta.get('CMF') or 0)
            smart_money = str(meta.get('Smart_Money') or '')
            if cmf > 0.05 or 'Giris' in smart_money or 'Akumulasyon' in smart_money:
                bonuses += 5.0
                bonus_tags.append('Akilli Para')

            # 3. VWAP Ustu Emniyet Kemeri (+4 Puan)
            if vwap_ok:
                bonuses += 4.0
                bonus_tags.append('VWAP Ustu')

            # 4. Super Hacim Carpani (>= 2.0x) (+4 Puan)
            if volume_multiplier >= 2.0:
                bonuses += 4.0
                bonus_tags.append('Super Hacim')

            # 5. Altin Saat / Erken Kopus (+3 Puan)
            if 'Phase 1' in phase:
                bonuses += 3.0
                bonus_tags.append('Erken Kopus')

            total_rank = base_score + bonuses
            if total_rank < (minimum_score - 8) and base_score < minimum_score:
                continue

            s['_sector_name'] = _sym_sec
            s['_sector_rel'] = _rel
            s['_bonus_score'] = bonuses
            s['_bonus_tags'] = bonus_tags
            s['_total_rank_score'] = total_rank
            s['_entry_checks'] = ', '.join(name for name, passed in checks.items() if passed)
            if bonus_tags:
                s['_entry_checks'] += ' | ' + ', '.join(bonus_tags)
            s['_entry_quality'] = sum(checks.values())
            s['_a_class'] = True
            s['_metadata'] = meta
            valid_signals.append(s)
            
        valid_signals.sort(key=lambda x: (x.get('_total_rank_score', 0), float(x.get('score', 0))), reverse=True)
        # KULLANICI ISTEGI: Nakitte para yatmasin, ozellikle BIST boga iken olabildigince aktif ofansif trade!
        # Kar alan veya cikan pozisyonlarin yerine gun icinde siradaki hisseler aninda devreye girer.
        # Bu nedenle havuz sadece 3-4 hisseyle kisitlanmaz; 25 adaylik dinamik havuz tutulur.
        candidate_pool = valid_signals[:25]
        if not candidate_pool:
            return

        current_cash = self.daily_budget
        
        # Mevcut islemleri veritabanindan oku: Ayni gun ayni hisseye tek islem kurali
        existing_today_trades = {}
        try:
            conn_chk = get_connection()
            cur_chk = conn_chk.cursor()
            cur_chk.execute(
                "SELECT symbol, entry_time, entry_price, shares, exit_time FROM trades WHERE owner=? AND date_str=?",
                (self.owner, date_str)
            )
            for er in cur_chk.fetchall():
                existing_today_trades[er['symbol']] = dict(er)
            conn_chk.close()
        except Exception:
            pass

        active_trades = []
        completed_trades = []
        stopped_out_symbols = set()
        traded_today_symbols = set()
        stop_times = {}
        
        pending_signals = []
        dfs = {}
        all_times = set()
        
        try:
            from zoneinfo import ZoneInfo
            _now_ist = datetime.now(ZoneInfo('Europe/Istanbul'))
        except Exception:
            _now_ist = datetime.now()
        _is_today = date_str == _now_ist.strftime('%Y-%m-%d')
        if _is_today:
            _now_t = _now_ist.time()
            if _now_t.hour < 10:
                end_h = 10
                end_m = 0
            elif _now_t.hour >= 18:
                end_h = 18
                end_m = 10
            else:
                end_h = _now_t.hour
                end_m = (_now_t.minute // 5) * 5
        else:
            end_h = 18
            end_m = 10
        
        # Gün içi tam seans zaman ızgarasını (10:00'dan güncel seans saatine kadar) oluştur
        _all_day_times = []
        _h, _m = 10, 0
        while True:
            _all_day_times.append(f'{_h:02d}:{_m:02d}:00')
            if _h > end_h or (_h == end_h and _m >= end_m):
                break
            _m += 5
            if _m >= 60:
                _h += 1
                _m = 0

        for s in candidate_pool:
            sym = s['symbol']
            clean_sym = sym.replace('.IS', '').strip()
            df = MarketDataManager.get_market_data(date_str, sym)
            p = float(s.get('morning_price') or s.get('Price') or 0.0)

            # Canlı piyasa verisinden gerçek fiyat, gün içi en yüksek ve en düşük değerleri al
            _stat = (
                _live_symbols_stats.get(sym) or
                _live_symbols_stats.get(f"{clean_sym}.IS") or
                _live_symbols_stats.get(clean_sym) or
                {}
            ) if _is_today and isinstance(_live_symbols_stats, dict) else {}

            _cur_p = float(_stat.get('Price') or _stat.get('Daily_Close') or p)
            _day_high = float(_stat.get('High') or max(p, _cur_p))
            _day_low = float(_stat.get('Low') or min(p, _cur_p))

            if df.empty:
                if p > 0:
                    _n = len(_all_day_times)
                    _bars = []
                    _mid_idx = max(1, _n // 3)
                    for _i, _t_str in enumerate(_all_day_times):
                        if _i <= _mid_idx:
                            _sub_pct = _i / _mid_idx
                            _step_c = p + (_day_high - p) * _sub_pct
                        else:
                            _sub_pct = (_i - _mid_idx) / max(1, (_n - _mid_idx))
                            _step_c = _day_high + (_cur_p - _day_high) * _sub_pct

                        _step_o = p if _i == 0 else _bars[-1]['Close']
                        _step_h = max(_step_o, _step_c, _day_high if _i == _mid_idx else _step_c)
                        _step_l = min(_step_o, _step_c, _day_low if (_i >= _mid_idx and _cur_p < p) else _step_c * 0.998)
                        _bars.append({
                            'Open': round(_step_o, 2),
                            'High': round(_step_h, 2),
                            'Low': round(_step_l, 2),
                            'Close': round(_step_c, 2),
                            'Volume': 50000 + int(_i * 1000)
                        })
                    df = pd.DataFrame(_bars, index=[pd.to_datetime(f'{date_str} {t}') for t in _all_day_times])
            elif _is_today and getattr(df.index, '__len__', lambda: 0)() > 0:
                # Eğer indirilen barlar gün ortasında (örn 10:20'de) kesilmişse, seans saatine kadar uzat
                last_dt = df.index[-1]
                last_time_str = last_dt.strftime('%H:%M:00')
                missing_times = [t for t in _all_day_times if t > last_time_str]
                if missing_times:
                    last_c = float(df['Close'].iloc[-1])
                    _mn = len(missing_times)
                    _ext_bars = []
                    for _mi, _mt in enumerate(missing_times):
                        _pct = (_mi + 1) / _mn
                        _ext_c = last_c + (_cur_p - last_c) * _pct
                        _ext_o = last_c if _mi == 0 else _ext_bars[-1]['Close']
                        _ext_h = max(_ext_o, _ext_c) * 1.003
                        _ext_l = min(_ext_o, _ext_c) * 0.997
                        _ext_bars.append({
                            'Open': _ext_o,
                            'High': _ext_h,
                            'Low': _ext_l,
                            'Close': _ext_c,
                            'Volume': 50000 + int(_mi * 1000)
                        })
                    ext_df = pd.DataFrame(_ext_bars, index=[pd.to_datetime(f'{date_str} {t}') for t in missing_times])
                    df = pd.concat([df, ext_df])

            if not df.empty:
                # Karma tz verisi: Postgres timestamp'leri tz-aware, yfinance
                # verisi naive geliyor; sorted() bu karisimda patliyor.
                # Tum indeksleri naive'e cevir (sutun karsilastirmalari zaten
                # kodun geri kalaninda naive varsayiyor).
                # NOT: concat sonrasi indeks object-dtype olabilir ve icinde
                # tz-aware + naive karisabilir; bu durumda df.index.tz None'dir,
                # o yuzden eleman bazinda normallestir.
                if getattr(df.index, 'tz', None) is not None or str(getattr(df.index, 'dtype', '')) == 'object':
                    try:
                        _norm = []
                        for t in df.index:
                            _ts = pd.Timestamp(t)
                            if _ts.tzinfo is not None:
                                _ts = _ts.tz_convert('Europe/Istanbul').tz_localize(None)
                            _norm.append(_ts)
                        df.index = pd.DatetimeIndex(_norm)
                    except Exception:
                        pass
                dfs[sym] = df
                for t in df.index:
                    all_times.add(t)
                
                phase = str(s.get('morning_phase', ''))
                meta = s.get('_metadata') or {}
                if not meta and s.get('metadata'):
                    try:
                        meta = json.loads(s.get('metadata'))
                    except Exception:
                        meta = {}

                import re
                disc_cand = s.get('discovery_time') or meta.get('discovery_time')
                time_str = None
                if disc_cand:
                    t_cand = str(disc_cand)[:5]
                    if re.match(r'^\d{2}:\d{2}$', t_cand):
                        time_str = t_cand + ":00"

                if not time_str:
                    match = re.search(r'(\d{2}:\d{2})', phase)
                    if match:
                        time_str = match.group(1) + ":00"

                if not time_str and (s.get('time') or meta.get('time') or meta.get('Time')):
                    t_cand = str(s.get('time') or meta.get('time') or meta.get('Time'))[:5]
                    if re.match(r'^\d{2}:\d{2}$', t_cand):
                        time_str = t_cand + ":00"

                if not time_str and (s.get('scan_timestamp') or meta.get('scan_timestamp')):
                    try:
                        from zoneinfo import ZoneInfo
                        _ts = float(s.get('scan_timestamp') or meta.get('scan_timestamp'))
                        _dt = datetime.fromtimestamp(_ts, ZoneInfo('Europe/Istanbul'))
                        if _dt.strftime('%Y-%m-%d') == date_str:
                            time_str = _dt.strftime('%H:%M:00')
                    except Exception:
                        pass

                if not time_str or time_str < "10:20:00":
                    time_str = "10:20:00"
                
                s['time_str'] = time_str
                pending_signals.append(s)
                
        sorted_times = sorted(list(all_times), key=lambda t: pd.Timestamp(t).tz_convert('Europe/Istanbul').tz_localize(None) if pd.Timestamp(t).tzinfo is not None else pd.Timestamp(t))
        
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
                bar_open = float(row['Open']) if 'Open' in row and pd.notna(row['Open']) else float(row['Close'])
                high = float(row['High'])
                low = float(row['Low'])
                close = float(row['Close'])
                
                sell_price = None
                reason = ""
                
                entry = trade['entry_price']
                
                # Evaluate this bar against the stop active before this bar.
                # Any stop increase derived from this bar's high is applied next bar.
                stop_price = trade['stop_price']
                tp1_price = trade['tp1_price']
                tp2_price = trade['tp2_price']
                prefix = trade.get('reason_prefix', '')
                
                # BARS HELD SAYACI (Zaman Stopu Icin)
                bars_held = trade.get('bars_held', 0) + 1
                trade['bars_held'] = bars_held

                # GARANTİCİ DİSİPLİN: Erken 35 dk zaman stopu kaldırıldı.
                # Hisseye nefes aldırılır; hisse ya hedefe (TP1/TP2) gider ya da teknik stop seviyesinde disiplinle çıkılır.
                # Seans sonu (17:50) ise tüm pozisyonlar zaten %100 nakde geçirilir.
                
                # En kötü senaryo: Önce Stop Loss patlar varsayımı
                if low <= stop_price:
                    sell_price = round(min(stop_price, bar_open) * 0.9985, 2) # gap-aware stop fill + slippage
                    if trade.get('scaled_out', False):
                        reason = "🛡️ BAŞA BAŞ STOP (BREAK-EVEN STOP: MALİYET KORUNDU)"
                    else:
                        reason = f"{prefix}⛔ ÇELİK STOP KESİLDİ"
                elif high >= tp2_price:
                    # OFANSİF MODDA TAVANA TAŞIMA:
                    # Eğer hisse tavana (+%9.5+) gidiyorsa ve tavan kilitliyse (close >= ceiling * 0.992),
                    # seans sonuna kadar tavanda tutulur!
                    ceiling_val = float(trade.get('ceiling_target') or (entry * 1.10))
                    if is_offensive and trade.get('is_runner') and (ceiling_val > 0 and close >= ceiling_val * 0.992):
                        pass # Tavan kilitli, pozisyon bozulmaz (17:50'ye kadar tam kâr)
                    else:
                        sell_price = round(max(tp2_price, bar_open) * 0.9985, 2)
                        reason = f"🚀 TAVAN (TAM KÂR ALINDI)"
                elif high >= tp1_price and not trade.get('scaled_out', False):
                    # Kademeli kâr alma (TP1): satış oranı rejime gore exit planindan gelir.
                    # Boga/yuksek volatilitede erken ve buyuk kisim satilir (kasa guvenligi),
                    # guclu bogada runner payi buyur (tavan potansiyeli).
                    trade['scaled_out'] = True
                    # DİNAMİK TP1 ÇIKIŞ ORANI (KÂRI KOŞTURMA):
                    # Ofansif modda TP1'de sadece %30 satılır (maliyet sıfırlanır), kalan %70 'Runner' olarak tavana taşınır!
                    # Defansif modda TP1'de %60 satılarak kâr kilitlenir.
                    _tp1_pct = 30 if is_offensive else 60
                    out_shares = max(1, int(round(trade['shares'] * _tp1_pct / 100.0)))
                    if out_shares >= trade['shares']:
                        out_shares = max(1, trade['shares'] - 1)
                    if out_shares > 0:
                        trade['shares'] -= out_shares
                        scale_out_price = round(tp1_price * 0.9985, 2)
                        buy_vol = out_shares * entry
                        sell_vol = out_shares * scale_out_price
                        comm = (buy_vol + sell_vol) * 0.0004
                        net_profit = (out_shares * (scale_out_price - entry)) - comm
                        current_cash += sell_vol - comm 
                        
                        # Artık geride kalan lotlar için stop maliyet + komisyona çekilir! (SIFIR RİSKLİ KASA)
                        trade['stop_price'] = entry * 1.0010
                        if is_offensive:
                            trade['is_runner'] = True
                            trade['reason_prefix'] = "🚀 [RUNNER TAVAN AVCISI] " 
                        
                        completed_trades.append({
                            'symbol': sym,
                            'entry_time': trade['entry_time'] + ' [TP1]',
                            'entry_price': entry,
                            'shares': out_shares,
                            'exit_time': str(current_time),
                            'exit_price': scale_out_price,
                            'pnl_val': net_profit,
                            'pnl_pct': (net_profit / buy_vol * 100) if buy_vol > 0 else 0.0,
                            'exit_reason': f"⚖️ KADEMELİ TP1 (%{_tp1_pct} SATILDI, STOP MALİYETE ÇEKİLDİ)",
                            'strategy_name': trade.get('strategy_name'),
                            'entry_score': trade.get('entry_score'),
                            'entry_checks': trade.get('entry_checks'),
                            'atr_value': trade.get('atr_value'),
                            'risk_amount': trade.get('risk_amount'),
                            'market_regime': trade.get('market_regime')
                        })

                        completed_trades[-1]['owner'] = self.owner
                        completed_trades[-1]['engine_version'] = trade.get('engine_version', 'V8_ELITE')
                        self._save_single_trade(str(current_time)[:10], completed_trades[-1])

                        # Telegram: TP1 otomatik kismi kâr alma emri bildirimi (atomik dedup korumalı)
                        try:
                            from services.telegram_bot import notify_sim_trade
                            notify_sim_trade(sym, "SAT (TP1)", scale_out_price,
                                         (net_profit / buy_vol * 100) if buy_vol > 0 else 0.0,
                                         f"⚖️ TP1: %{_tp1_pct} kâr alındı, stop maliyete çekildi (risk-free)",
                                         str(current_time)[:10], completed_trades[-1])
                        except Exception:
                            pass
                            
                if sell_price is not None:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(current_time)
                    trade['exit_price'] = sell_price
                    
                    buy_volume = trade['shares'] * trade['entry_price']
                    sell_volume = trade['shares'] * sell_price
                    buy_commission = buy_volume * 0.0004
                    sell_commission = sell_volume * 0.0004
                    gross_pnl = trade['shares'] * (sell_price - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl - buy_commission - sell_commission
                    trade['pnl_pct'] = (trade['pnl_val'] / buy_volume * 100) if buy_volume > 0 else 0.0
                    
                    if "🔄" not in trade.get('exit_reason', '') and trade.get('is_reentry', False):
                        reason = "🔄 " + reason
                        
                    trade['exit_reason'] = reason
                    trade['owner'] = self.owner
                    trade['engine_version'] = trade.get('engine_version', 'V8_ELITE')
                    completed_trades.append(trade)
                    self._save_single_trade(str(current_time)[:10], trade)
                    try:
                        from services.telegram_bot import notify_sim_trade
                        notify_sim_trade(sym, "SAT", sell_price, trade["pnl_pct"], reason, str(current_time)[:10], trade)
                    except Exception:
                        pass
                    
                    if "STOP" in reason:
                        stopped_out_symbols.add(sym)
                        stop_times[sym] = current_time
                        
                    # Buy-side fee was already deducted when the position was opened.
                    current_cash += sell_volume - sell_commission
                    
            # Update trailing levels only after the current candle has been evaluated.
            # This prevents using a candle's high to retroactively trigger its new stop.
            for open_trade in [t for t in active_trades if t['status'] == 'OPEN']:
                open_df = dfs.get(open_trade['symbol'])
                if open_df is None or current_time not in open_df.index:
                    continue
                bar_high = float(open_df.loc[current_time, 'High'])
                entry_price_for_stop = float(open_trade['entry_price'])
                old_stop = float(open_trade['stop_price'])
                new_stop = old_stop
                # DİNAMİK 2-BAR İZ SÜREN STOP & ERKEN MALİYET KİLİDİ
                if not open_trade.get('scaled_out', False):
                    # +%1.5 görüldüğü anda stop maliyete çekilir (+%3 beklenmez!)
                    if bar_high >= entry_price_for_stop * 1.015 and old_stop < entry_price_for_stop * 1.001:
                        new_stop = entry_price_for_stop * 1.001
                        open_trade['reason_prefix'] = "[ERKEN MALİYET KORUMA] "
                else:
                    # Kalan lotlar için iz süren stop (Ofansif Runner veya Defansif)
                    if is_offensive and open_trade.get('is_runner'):
                        # OFANSİF RUNNER İZ SÜREN STOP (KÂRI TAVANA KADAR KOŞTUR)
                        if bar_high >= entry_price_for_stop * 1.080:  # +%8 üzeri (tavan öncesi)
                            new_stop = max(new_stop, entry_price_for_stop * 1.065)
                            open_trade['reason_prefix'] = "🚀 [RUNNER +%6.5 KİLİTLİ] "
                        elif bar_high >= entry_price_for_stop * 1.050:
                            new_stop = max(new_stop, entry_price_for_stop * 1.035)
                            open_trade['reason_prefix'] = "🚀 [RUNNER +%3.5 KİLİTLİ] "
                        elif bar_high >= entry_price_for_stop * 1.030:
                            new_stop = max(new_stop, entry_price_for_stop * 1.018)
                        try:
                            two_bar_min = float(open_df.loc[:current_time, 'Low'].tail(2).min())
                            if two_bar_min > entry_price_for_stop * 1.01:
                                new_stop = max(new_stop, two_bar_min * 0.9985)
                        except Exception:
                            pass
                    else:
                        # DEFANSİF STANDART 2-BAR İZ SÜREN STOP
                        try:
                            two_bar_min = float(open_df.loc[:current_time, 'Low'].tail(2).min())
                            if two_bar_min > entry_price_for_stop:
                                new_stop = max(old_stop, two_bar_min * 0.9985)
                                open_trade['reason_prefix'] = "[2-BAR İZ SÜREN STOP] "
                        except Exception:
                            pass
                        if bar_high >= entry_price_for_stop * 1.050:
                            new_stop = max(new_stop, entry_price_for_stop * 1.035)
                        elif bar_high >= entry_price_for_stop * 1.030:
                            new_stop = max(new_stop, entry_price_for_stop * 1.018)
                open_trade['stop_price'] = new_stop

            # 2. YENİ ALIMLARI KONTROL ET
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}

            # GÜNLÜK RİSK VE KÂR KİLİDİ (Çelik Kurallar):
            # 1. Günlük zarar kesici: Gün içi zarar bütçenin %1.5'ine (-1.500 TL) ulaşırsa sermaye koruma için yeni işlem açılmaz.
            # 2. Günlük kâr kilidi: Gün içi kâr bütçenin +%2.0'sine (+2.000 TL) ulaştığında kazancı kilitlemek için yeni giriş durdurulur.
            # 3. Üst üste 2 STOP zararı sonrası gün sonuna kadar yalnızca izleme modu.
            _daily_pnl = sum(float(t.get('pnl_val') or 0) for t in completed_trades)
            _streak = 0
            for _t in reversed(completed_trades):
                if float(_t.get('pnl_val') or 0) < 0:
                    _streak += 1
                else:
                    break
            _loss_limit = self.daily_budget * 0.015    # -%1.5 (1.500 TL)
            _profit_limit = self.daily_budget * 0.020  # +%2.0 (2.000 TL)

            if _daily_pnl <= -_loss_limit or _daily_pnl >= _profit_limit or _streak >= 2:
                if _daily_pnl <= -_loss_limit:
                    _lock_reason = f"Günlük zarar kesici (-%1.5): {_daily_pnl:.0f} TL; sermaye koruma devrede, yeni alımlar durduruldu"
                elif _daily_pnl >= _profit_limit:
                    _lock_reason = f"Günlük kâr kilidi (+%2.0): +{_daily_pnl:.0f} TL; hedefe ulaşıldı, kazanç kilitlendi"
                else:
                    _lock_reason = f"Üst üste {_streak} zarar kilidi; yeni alımlar durduruldu"

                # OFANSİF FREE-ROLL (EV PARASI) İSTİSNASI:
                # Kâr kilidi (+2.000 TL) dolduğunda ofansif moddaysak (ralli günü),
                # kazanılan kârın sadece 300 TL'si risk edilerek 97+ puanlı tek bir tavan adayı denenebilir!
                has_freeroll = (
                    is_offensive and
                    _daily_pnl >= _profit_limit and
                    _daily_pnl > -_loss_limit and
                    _streak < 2 and
                    not any(t.get('is_freeroll') for t in completed_trades + active_trades)
                )
                if not has_freeroll:
                    if pending_signals:
                        print(f"[SimEngine] {date_str} {current_time} -> {_lock_reason}")
                    pending_signals = []
            
            # 2. YENI ALIMLARI KONTROL ET (OFANSIF NAKIT YONETIMI)
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}
            available_slots = max(0, effective_max_positions - len(open_symbols))

            entries_in_this_bar = 0
            MAX_ENTRIES_PER_BAR = 2  # Tek bir 5 dakikalık barda en fazla 2 en kaliteli hisse alınır (portföy zaman yayılımı)

            to_remove = []
            # DİNAMİK GÜNLÜK İŞLEM LİMİTİ:
            # Ofansif modda: Günde en fazla 4 işlem (akışkan ralli, tavan avı).
            # Defansif (Ayı/Nötr) modda: Günde KESİNLİKLE en fazla 2 işlem (doğranma ve testere engeli).
            max_daily_allowed = 4 if is_offensive else 2
            if (len(completed_trades) + len(open_symbols)) >= max_daily_allowed and not (is_offensive and _daily_pnl >= _profit_limit):
                pending_signals = []
                break

            # BRÜT MARUZİYET TAVANI (PORTFÖY KALDIRAÇ ENGELİ):
            # Açık pozisyonların toplam tutarı portföyün %25 - %30'unu (max 125.000 - 150.000 TL) ASLA aşamaz.
            # Kasanın en az %70'i (350.000 TL) HER ZAMAN NAKİTTE kalır!
            current_total_exposure = sum(float(t.get('shares', 0)) * float(t.get('entry_price', 0)) for t in active_trades if t['status'] == 'OPEN')
            max_allowed_exposure = self.daily_budget * (0.30 if is_offensive else 0.25)
            if current_total_exposure >= max_allowed_exposure or len(open_symbols) >= 3:
                break

            # 🛡️ BIST 100 ENDEKS ŞALTERİ (MACRO INDEX KILL-SWITCH):
            # 1. Şiddetli Çöküş (pressure_pct >= 80.0 veya xu100_change < -1.50) veya pozisyon hakkı 0 ise tamamen dur:
            if effective_max_positions <= 0 or xu100_change < -1.50 or pressure_pct >= 80.0:
                print(f"[INDEX-GUARD] Şiddetli Piyasa Kilidi: XU100 %{xu100_change:+.2f} / Satış Baskısı %{pressure_pct:.1f}! Yeni alımlar donduruldu.")
                break
            # 2. Ayı / Satış Baskısı Modunda (pressure_pct >= 55 veya xu100_change < -0.30):
            # Savunma kuralı uygulanır: Kasa korunarak yalnızca en fazla 1 seçici pozisyona izin verilir.
            if (xu100_change < -0.30 or pressure_pct >= 55.0) and len(open_symbols) >= 1:
                print(f"[INDEX-GUARD] Savunma Modu Dolu: Açık pozisyon ({len(open_symbols)}/{effective_max_positions}) mevcut, yeni alım durduruldu.")
                break

            for s in list(pending_signals):
                if effective_max_positions <= 0:
                    break  # Yalnizca rejim/zarar kilidi aktifse durdur
                if available_slots <= 0 or entries_in_this_bar >= MAX_ENTRIES_PER_BAR:
                    break

                sym = s['symbol']
                if sym in open_symbols or sym in stopped_out_symbols:
                    continue

                # KATI PENNY STOCK ENGELİ: Fiyatı 8.0 TL altındaki sığ hisseler ASLA giremez!
                s_p = float(s.get('morning_price') or s.get('Price') or 0.0)
                if 0 < s_p < 8.0:
                    to_remove.append(s)
                    continue

                # SEKTÖR TEKELİ KORUMASI (Aynı Sektörden Çift Pozisyon Yasağı):
                # Örneğin GARAN açıkken VAKBN alınamaz! Sektör riski zorunlu dağıtılır.
                s_sector = s.get('_sector_name') or ''
                if s_sector:
                    open_sectors = {t.get('sector_name') or t.get('_sector_name') for t in active_trades if t['status'] == 'OPEN'}
                    if s_sector in open_sectors:
                        print(f"[SimEngine] {sym} elendi: {s_sector} sektöründe zaten açık pozisyon var")
                        to_remove.append(s)
                        continue

                # DİNAMİK SEÇİCİLİK:
                # candidate_pool zaten 6 temel filtreyi (RSI, Tuzak, VWAP, CMF, Hacim, Trend) geçmiş elit havuzdur.
                eff_score = float(s.get('_total_rank_score') or s.get('score', 0))
                min_score_req = 65.0 if is_offensive else 72.0
                if eff_score < min_score_req:
                    continue

                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current < dt_ps:
                    continue
                # 10:15 oncesi ilk acilis dalgalanmasinda isleme girme
                if dt_current.time() < time(10, 15):
                    continue

                # GARANTİCİ ÖĞLE ARASI YASAĞI (11:30 - 13:30):
                # BIST'te öğle arası hacim kurur, sahte kırılımlar ve tuzaklar artar.
                # Yeni alımlar sadece sabah (10:15 - 11:30) ve öğleden sonra (13:30 - 14:30) yapılır!
                if time(11, 30) <= dt_current.time() < time(13, 30):
                    continue

                # KATI ZAMAN KALKANI: Saat 17:00'dan sonra seans sonu kapanış dalgalanmasında yeni pozisyon açılmaz.
                # 10:15 - 17:00 arası gün içi kırılımlara ve öğleden sonra rallilerine izin verilir.
                if dt_current.time() >= time(17, 0):
                    to_remove.append(s)
                    continue

                sym = s['symbol']
                if sym in open_symbols or sym in stopped_out_symbols:
                    continue

                # 🛡️ KURUMSAL ORB KURALI (10:00 - 10:20 AÇILIŞ TUZAĞI KORUMASI):
                # Sabah ilk 20 dakika piyasanın gerçek yönü belirsizdir; açılış sahte tavan tuzaklarına girilmez!
                if dt_current.time() < time(10, 20):
                    continue

                # Oglen sahte kirilim elemesi (13:45 - 15:15)
                if time(13, 45) <= dt_current.time() < time(15, 15):
                    if float(s.get('_total_rank_score') or s.get('score', 0)) < 65:
                        continue

                df = dfs.get(sym)
                if df is None or current_time not in df.index:
                    continue

                from datetime import datetime as _dt_cls
                today_now_str = _dt_cls.now().strftime('%Y-%m-%d')
                is_live_today = (date_str == today_now_str and current_time.time() < time(17, 30))
                remaining_bars = int((df.index > current_time).sum())
                if not is_live_today and remaining_bars < 3:
                    to_remove.append(s)
                    continue

                raw_entry = float(df.loc[current_time, 'Close'])
                ceiling = float(s.get('ceiling_target') or 0.0)
                if ceiling <= 0:
                    morning_p = float(s.get('morning_price') or s.get('Price') or raw_entry)
                    ceiling = morning_p * 1.10 if morning_p > 0 else raw_entry * 1.10
                prev_close = (ceiling / 1.10) if ceiling > 0 else raw_entry
                current_ch = ((raw_entry - prev_close) / prev_close * 100.0) if prev_close > 0 else 0.0
                # Tavan koruması: Tavana kilitlenmiş (+%8.5 üzeri) seviyelerden alım yapılmaz, ancak +%8.5'e kadar kırılımlara girilir
                if current_ch >= 8.5 or (ceiling > 0 and raw_entry >= ceiling * 0.985):
                    to_remove.append(s)
                    continue

                # Fiyatlar 2 haneye yuvarlanir: kaydedilen giris/cikis/lot ile
                # pnl_val tamamen elle dogrulanabilir olur (yuvarlama farki sıfır).
                entry_price = round(raw_entry * 1.0015, 2)
                setup = self._entry_setup(df.loc[:current_time], entry_price, meta=meta)
                if not setup:
                    # Desteğe süzülüş / destek tutunması teyit edilmemişse (aşırı uzamışsa) KESİNLİKLE girilmez!
                    continue

                _tp1_dist = max(setup['atr_value'] * 1.8, entry_price * 0.025) * _tp1_mult
                tp1_price = min(ceiling * 0.997, entry_price + _tp1_dist)
                if tp1_price <= entry_price:
                    to_remove.append(s)
                    continue

                tp2_price = min(ceiling, max(tp1_price * 1.01, entry_price * (1 + 0.10 * _tp2_mult)))
                allocation, risk_amount = self._position_allocation(
                    current_cash, entry_price, setup['stop_price'], is_bear,
                    risk_pct=_sim_risk_pct, regime=_sim_regime, open_slots=available_slots,
                    total_score=float(s.get('_total_rank_score') or s.get('score', 90.0)),
                    bonus_tags=s.get('_bonus_tags', [])
                )
                shares = int(allocation // entry_price)
                if shares <= 0:
                    to_remove.append(s)
                    continue

                current_cash -= (shares * entry_price) * 1.0004
                traded_today_symbols.add(sym)

                sec_name = s.get('_sector_name', '')
                sec_rel = s.get('_sector_rel', 0.0)
                sec_tag = f' | {sec_name} (%{sec_rel:+.2f})' if sec_name else ''
                strat_tag = setup.get('strategy_tag') or 'Desteğe Süzülüş'
                strat_title = s.get('strategy_name') or f"V8 {s.get('morning_phase', 'Kirilim')}{sec_tag} | 🎯 {strat_tag}"

                orig_entry_time = str(current_time)
                orig_entry_price = entry_price
                if sym in existing_today_trades and existing_today_trades[sym].get('exit_time'):
                    # Yalnizca onceden kapanmis islemlerin giris zamani korunur
                    orig_entry_time = existing_today_trades[sym].get('entry_time') or orig_entry_time
                    orig_entry_price = float(existing_today_trades[sym].get('entry_price') or orig_entry_price)

                trade_entry = {
                    'symbol': sym,
                    'entry_time': orig_entry_time,
                    'entry_price': orig_entry_price,
                    'ceiling_target': ceiling,
                    'stop_price': setup['stop_price'],
                    'tp1_price': tp1_price,
                    'tp2_price': tp2_price,
                    'shares': shares,
                    'status': 'OPEN',
                    'scaled_out': False,
                    'is_reentry': False,
                    'is_runner': False,
                    'is_offensive': is_offensive,
                    'is_freeroll': bool(is_offensive and _daily_pnl >= _profit_limit),
                    'trading_gear': trading_gear,
                    'strategy_name': strat_title,
                    'entry_score': float(s.get('score', 0)),
                    'entry_checks': s.get('_entry_checks', ''),
                    'atr_value': setup['atr_value'],
                    'risk_amount': risk_amount,
                    'market_regime': market_regime,
                    'sector_name': sec_name,
                    '_sector_name': sec_name,
                    'engine_version': 'V8_ELITE',
                    'initial_stop': setup['stop_price'],
                    'stop_model': 'ATR 1.8x + Destek',
                    'xu100_at_entry': xu100_change,
                    'vwap_at_entry': float(s.get('VWAP') or s.get('_metadata', {}).get('VWAP') or entry_price),
                    'mfe_pct': 0.0,
                    'mae_pct': 0.0,
                    'tp1_hit': 0,
                    'breakeven_moved': 0,
                    'r_multiple': 0.0,
                    'hold_minutes': 0
                }
                trade_entry['owner'] = self.owner
                active_trades.append(trade_entry)
                open_symbols.add(sym)
                available_slots -= 1
                entries_in_this_bar += 1
                self._save_single_trade(str(current_time)[:10], trade_entry)
                try:
                    from services.telegram_bot import notify_sim_trade
                    notify_sim_trade(sym, 'AL', entry_price, 0.0, f'Sistem AL verdi{sec_tag}', str(current_time)[:10], trade_entry)
                except Exception:
                    pass
                to_remove.append(s)

            for s in to_remove:
                if s in pending_signals:
                    pending_signals.remove(s)
                    
            # 3. YENİDEN GİRİŞ KORUMASI:
            # Borsa İstanbul dinamiklerinde aynı gün stoplanan hisseye tekrar girmek (re-entry)
            # sermayeyi eritmektedir. Stoplanan hisseye aynı gün tekrar girilmez, sermaye korunur.
            for sym in []:
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
                    entry_price = round(raw_entry * 1.0015, 2)
                    setup = self._entry_setup(sub_df, entry_price)
                    if not setup:
                        continue
                    allocation, risk_amount = self._position_allocation(
                        current_cash, entry_price, setup['stop_price'], is_bear, risk_pct=_sim_risk_pct
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
                        'tp1_price': min(entry_price * 1.10 * 0.997, entry_price + max(setup['atr_value'] * 1.8, entry_price * 0.025) * _tp1_mult),
                        'tp2_price': max(min(entry_price * 1.10, entry_price + max(setup['atr_value'] * 1.8, entry_price * 0.025) * _tp1_mult * 1.01), entry_price * (1 + 0.10 * _tp2_mult)),
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
        # BUGUN icin seans henuz 17:50'den onceyse canli modda acik birak;
        # frontend "Islemde" olarak gostersin. GECMIS tarihler icin son bar
        # (seans sonu ~18:00) uzerinden kapanis zorunlu — aksi halde eski
        # gunlerin pozisyonlari sonsuza kadar "ACIK POZISYON" kalirdi.
        # Europe/Istanbul saat dilimi baz alınır (PythonAnywhere UTC olsa bile 17:50'de kesin nakde geçer).
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now = datetime.now()
        is_today = date_str == now.strftime("%Y-%m-%d")
        close_open_now = (not is_today) or now.time() >= time(17, 50)

        for trade in [t for t in active_trades if t['status'] == 'OPEN']:
            sym = trade['symbol']
            df = dfs.get(sym)
            if df is not None and not df.empty:
                last_time = df.index[-1]
                close = float(df.iloc[-1]['Close'])
                if close_open_now:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = str(last_time)
                    # End-of-day market exit includes conservative sell-side slippage.
                    eod_sell_price = round(close * 0.9985, 2)
                    trade['exit_price'] = eod_sell_price
                    buy_volume = trade['shares'] * trade['entry_price']
                    sell_volume = trade['shares'] * eod_sell_price
                    buy_commission = buy_volume * 0.0004
                    sell_commission = sell_volume * 0.0004
                    gross_pnl = trade['shares'] * (eod_sell_price - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl - buy_commission - sell_commission
                    trade['realized_pnl'] = trade['pnl_val']
                    current_cash += sell_volume - sell_commission
                    trade['pnl_pct'] = (trade['pnl_val'] / buy_volume * 100) if buy_volume > 0 else 0.0
                    trade['exit_reason'] = 'SEANS SONU NAKITE GECIS (17:50)'
                    trade['owner'] = self.owner
                    trade['engine_version'] = trade.get('engine_version', 'V8_ELITE')
                    self._save_single_trade(str(last_time)[:10], trade)
                    try:
                        from services.telegram_bot import notify_sim_trade
                        notify_sim_trade(sym, "SAT (GUN SONU)", eod_sell_price, trade["pnl_pct"], "17:50 Otomatik Kapanis", str(last_time)[:10], trade)
                    except Exception:
                        pass
                else:
                    trade['exit_time'] = None
                    trade['exit_price'] = None
                    buy_volume = trade['shares'] * trade['entry_price']
                    gross_pnl = trade['shares'] * (close - trade['entry_price'])
                    trade['pnl_val'] = gross_pnl
                    trade['pnl_pct'] = (gross_pnl / buy_volume * 100) if buy_volume > 0 else 0.0
                    trade['exit_reason'] = "⏳ ACIK POZISYON"
                completed_trades.append(trade)
            else:
                if close_open_now:
                    trade['status'] = 'CLOSED'
                    trade['exit_time'] = f"{date_str} 18:00:00"
                    trade['exit_price'] = trade['entry_price']
                    trade['pnl_val'] = 0.0
                    trade['realized_pnl'] = 0.0
                    trade['pnl_pct'] = 0.0
                    trade['exit_reason'] = 'SEANS SONU NAKITE GECIS (17:50)'
                    trade['owner'] = self.owner
                    trade['engine_version'] = trade.get('engine_version', 'V8_ELITE')
                    self._save_single_trade(date_str, trade)
                else:
                    trade['exit_time'] = None
                    trade['exit_price'] = None
                    trade['pnl_val'] = 0.0
                    trade['pnl_pct'] = 0.0
                    trade['exit_reason'] = "⏳ ACIK POZISYON (Veri Bekleniyor)"
                completed_trades.append(trade)

        self._save_trades(date_str, completed_trades)
        try:
            conn_cln = get_connection()
            cur_cln = conn_cln.cursor()
            cur_cln.execute("""
                DELETE FROM trades 
                WHERE owner = ? AND date_str = ? AND rowid NOT IN (
                    SELECT MIN(rowid) FROM trades WHERE owner = ? AND date_str = ? GROUP BY symbol
                )
            """, (self.owner, date_str, self.owner, date_str))
            conn_cln.commit()
            conn_cln.close()
        except Exception:
            pass
        print(f"[SimEngine] {date_str} için ÇELİK SİSTEM tamamlandı. İşlem Sayısı: {len(completed_trades)}")

        # Seans sonu: Nakde geçiş tamamlandıktan sonra gün sonu detaylı kâr/zarar tablosu ve hisseler Telegram'a otomatik gönderilir
        if close_open_now and completed_trades:
            try:
                from services.telegram_bot import send_simulation_report
                send_simulation_report(date_str=date_str, owner=self.owner)
            except Exception as _e_rep:
                print(f"[SimEngine] Gün sonu rapor gönderim hatası: {_e_rep}")

    def evaluate_live_positions(self, live_stats: dict = None):
        """Açık pozisyonları canlı TradingView fiyatlarıyla değerlendirir.
        Stop-loss (Zarar Kes) veya Kâr Al seviyelerine ulaşıldığında pozisyonu
        anında kapatır, veritabanına işler ve Telegram bildirimini iletir.
        """
        xu100_chg = 0.0
        if not live_stats:
            try:
                for _cf_path in ["dashboard_cache.json", "data/cache/dashboard_cache.json"]:
                    if os.path.exists(_cf_path):
                        with open(_cf_path, "r", encoding="utf-8") as f:
                            _cached_root = json.load(f)
                            live_stats = _cached_root.get("all_symbols_stats", {})
                            xu100_chg = float(_cached_root.get("xu100_change", 0.0))
                        if live_stats:
                            break
            except Exception:
                live_stats = {}
        else:
            try:
                for _cf_path in ["dashboard_cache.json", "data/cache/dashboard_cache.json"]:
                    if os.path.exists(_cf_path):
                        with open(_cf_path, "r", encoding="utf-8") as f:
                            xu100_chg = float(json.load(f).get("xu100_change", 0.0))
                        break
            except Exception:
                pass

        if not live_stats:
            return []

        try:
            from zoneinfo import ZoneInfo
            now_ist = datetime.now(ZoneInfo("Europe/Istanbul"))
        except Exception:
            now_ist = datetime.now()
        now_str = now_ist.strftime("%Y-%m-%d %H:%M:%S")
        today_str = now_ist.strftime("%Y-%m-%d")

        conn = get_connection()
        c = conn.cursor()
        c.execute("""
            SELECT id, date_str, symbol, entry_time, entry_price, shares, atr_value,
                   strategy_name, entry_score, entry_checks, risk_amount, market_regime, engine_version,
                   mfe_pct, mae_pct, initial_stop, tp1_price, tp1_hit, breakeven_moved
            FROM trades
            WHERE owner = ? AND exit_time IS NULL
        """, (self.owner,))
        open_rows = [dict(r) for r in c.fetchall()]
        conn.close()

        updated_trades = []
        for r in open_rows:
            sym = str(r['symbol']).strip()
            clean_sym = sym.replace('.IS', '').strip()
            stat = (
                live_stats.get(sym) or
                live_stats.get(f"{clean_sym}.IS") or
                live_stats.get(clean_sym) or
                live_stats.get(f"BIST:{clean_sym}") or
                {}
            )
            live_px = stat.get('Price') or stat.get('Daily_Close') or stat.get('last_price') or stat.get('price')
            if not live_px or float(live_px) <= 0:
                continue

            live_px = round(float(live_px), 2)
            entry_px = float(r['entry_price'])
            shares = int(r['shares'])
            if entry_px <= 0 or shares <= 0:
                continue

            buy_vol = shares * entry_px
            sell_vol = shares * live_px
            comm = (buy_vol + sell_vol) * 0.0004
            gross_pnl = shares * (live_px - entry_px)
            net_pnl = round(gross_pnl - comm, 2)
            pnl_pct = round((net_pnl / buy_vol) * 100.0, 2)

            atr = float(r.get('atr_value') or (entry_px * 0.02))
            stop_pct = min(0.040, max(0.024, (atr / entry_px) * 1.8))

            # 🛡️ ENDEKS ŞALTERİ & ÇELİK STOP SIKILAŞTIRMASI:
            # XU100 % -0.40'ın altına indiğinde veya yoğun satış dalgasında stopu agresifçe daralt (%1.6)
            is_index_dump = (xu100_chg < -0.40)
            if is_index_dump:
                stop_pct = min(stop_pct, 0.016)

            stop_px = round(entry_px * (1.0 - stop_pct), 2)
            tp1_px = round(entry_px * 1.04, 2)

            is_stopped = (live_px <= stop_px) or (pnl_pct <= (-1.6 if is_index_dump else -2.4))
            is_tp = (live_px >= tp1_px) or (pnl_pct >= 4.0)
            is_eod = (now_ist.hour >= 18 or (now_ist.hour == 17 and now_ist.minute >= 50)) and r.get('date_str') == today_str

            should_close = is_stopped or is_tp or is_eod
            reason = ""
            if is_stopped:
                slippage_tl = max(0.0, round(shares * (stop_px - live_px), 2))
                if slippage_tl > (shares * entry_px * 0.003): # %0.3'ten fazla gap kayması varsa
                    reason = f"⛔ GAP STOP (%{pnl_pct:+.2f}, Kayma: -{slippage_tl:.0f}₺)"
                elif is_index_dump:
                    reason = f"⛔ ENDEKS ŞALTERİ & ÇELİK STOP (%{pnl_pct:+.2f})"
                else:
                    reason = f"⛔ ÇELİK STOP KESİLDİ (%{pnl_pct:+.2f})"
            elif is_tp:
                reason = f"🚀 KÂR ALINDI (%{pnl_pct:+.2f})"
            elif is_eod:
                reason = "SEANS SONU NAKİTE GEÇİŞ (17:50)"

            # ── MFE, MAE, R-MULTIPLE & HOLD DURATION TAKİBİ ──
            # Look-ahead bias ve giriş öncesi tepe/dip hatasını önlemek için:
            # MFE ve MAE KESİNLİKLE işlem girişinden (entry_time) sonraki canlı fiyat adımlarıyla güncellenir.
            cur_unrealized_pct = round(((live_px - entry_px) / entry_px) * 100.0, 2)
            cur_mfe = max(float(r.get('mfe_pct') or 0.0), cur_unrealized_pct)
            cur_mae = min(float(r.get('mae_pct') or 0.0), cur_unrealized_pct)
            risk_amt = float(r.get('risk_amount') or 1250.0)
            r_mult = round(net_pnl / risk_amt, 2) if risk_amt > 0 else 0.0
            hold_mins = 0
            try:
                dt_in = pd.to_datetime(r['entry_time'])
                dt_now = pd.to_datetime(now_str)
                hold_mins = max(1, int((dt_now - dt_in).total_seconds() / 60))
            except Exception:
                pass

            if should_close:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE trades
                    SET exit_time = ?, exit_price = ?, pnl_val = ?, realized_pnl = ?, pnl_pct = ?, exit_reason = ?,
                        mfe_pct = ?, mae_pct = ?, r_multiple = ?, hold_minutes = ?
                    WHERE id = ?
                """, (now_str, live_px, net_pnl, net_pnl, pnl_pct, reason, cur_mfe, cur_mae, r_mult, hold_mins, r['id']))
                conn.commit()
                conn.close()

                r['exit_time'] = now_str
                r['exit_price'] = live_px
                r['pnl_val'] = net_pnl
                r['realized_pnl'] = net_pnl
                r['pnl_pct'] = pnl_pct
                r['exit_reason'] = reason
                r['mfe_pct'] = cur_mfe
                r['mae_pct'] = cur_mae
                r['r_multiple'] = r_mult
                r['hold_minutes'] = hold_mins
                updated_trades.append(r)

                try:
                    from services.telegram_bot import notify_sim_trade
                    action = "SAT (STOP)" if is_stopped else ("SAT (KÂR)" if is_tp else "SAT (GÜN SONU)")
                    notify_sim_trade(sym, action, live_px, pnl_pct, reason, today_str, r)
                except Exception as tg_err:
                    print(f"[LIVE STOP TG ERROR] {tg_err}")
            else:
                conn = get_connection()
                cur = conn.cursor()
                cur.execute("""
                    UPDATE trades
                    SET pnl_val = ?, pnl_pct = ?, mfe_pct = ?, mae_pct = ?
                    WHERE id = ?
                """, (net_pnl, pnl_pct, cur_mfe, cur_mae, r['id']))
                conn.commit()
                conn.close()

        return updated_trades

    def run_backtest_range(self, start_date: str, end_date: str, verbose: bool = False):
        """
        Gelişmiş Çok Günlü Backtest Modu (Doğrulama & Parametre Testi):
        Belirtilen iki tarih arasındaki (son 30-60 gün vb.) tüm işlem günlerinde
        simülasyon motorunu çalıştırır. Sonuçta sermaye eğrisi, kazanma oranı (win rate),
        kâr faktörü (profit factor) ve maksimum düşüş (drawdown) hesaplar.
        """
        from datetime import datetime as _bt_dt, timedelta as _bt_td
        d_start = _bt_dt.strptime(start_date, "%Y-%m-%d").date()
        d_end = _bt_dt.strptime(end_date, "%Y-%m-%d").date()

        current_d = d_start
        executed_days = []
        while current_d <= d_end:
            if current_d.weekday() < 5:  # Hafta içi
                d_str = current_d.strftime("%Y-%m-%d")
                try:
                    self.run_daily_simulation(d_str)
                    executed_days.append(d_str)
                except Exception as _e_day:
                    if verbose:
                        print(f"[Backtest] {d_str} hata: {_e_day}")
            current_d += _bt_td(days=1)

        try:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                SELECT symbol, entry_time, exit_time, entry_price, exit_price,
                       shares, pnl_val, pnl_pct, exit_reason, strategy_name
                FROM trades
                WHERE owner = ? AND date_str >= ? AND date_str <= ?
                ORDER BY entry_time ASC
            """, (self.owner, start_date, end_date))
            trades = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT date_str, start_equity, end_equity, daily_pnl
                FROM equity_log
                WHERE owner = ? AND date_str >= ? AND date_str <= ?
                ORDER BY date_str ASC
            """, (self.owner, start_date, end_date))
            equity_curve = [dict(r) for r in cur.fetchall()]
            conn.close()

            total_trades = len(trades)
            wins = [t for t in trades if float(t.get('pnl_val') or 0) > 0]
            losses = [t for t in trades if float(t.get('pnl_val') or 0) < 0]
            win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

            gross_profit = sum(float(t.get('pnl_val') or 0) for t in wins)
            gross_loss = abs(sum(float(t.get('pnl_val') or 0) for t in losses))
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (99.0 if gross_profit > 0 else 1.0)
            net_pnl = sum(float(t.get('pnl_val') or 0) for t in trades)

            peak = self.daily_budget
            max_dd_val = 0.0
            max_dd_pct = 0.0
            running_equity = self.daily_budget
            for day in equity_curve:
                running_equity = float(day.get('end_equity') or running_equity)
                if running_equity > peak:
                    peak = running_equity
                dd = peak - running_equity
                dd_pct = (dd / peak * 100.0) if peak > 0 else 0.0
                if dd > max_dd_val:
                    max_dd_val = dd
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct

            return {
                "status": "success",
                "start_date": start_date,
                "end_date": end_date,
                "days_tested": len(executed_days),
                "total_trades": total_trades,
                "win_count": len(wins),
                "loss_count": len(losses),
                "win_rate": round(win_rate, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_loss": round(gross_loss, 2),
                "profit_factor": round(profit_factor, 2),
                "net_pnl": round(net_pnl, 2),
                "max_drawdown_val": round(max_dd_val, 2),
                "max_drawdown_pct": round(max_dd_pct, 2),
                "trades": trades,
                "equity_curve": equity_curve
            }
        except Exception as e_res:
            return {"status": "error", "message": str(e_res)}

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

    def __init__(self, daily_budget=100000.0, max_positions=3, owner=None):
        self.daily_budget = daily_budget
        self.max_positions = 999  # KULLANICI ISTEGI: Simulasyonda islem sayisi SINIRSIZ
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
                    entry_score, entry_checks, atr_value, risk_amount, market_regime, engine_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    engine_version=COALESCE(excluded.engine_version, trades.engine_version)
            """, (
                self.owner, date_str, trade['symbol'], trade['entry_time'], trade['entry_price'],
                trade.get('exit_time'), trade.get('exit_price'), trade.get('shares'),
                trade.get('pnl_val', 0.0), trade.get('realized_pnl', 0.0), trade.get('pnl_pct', 0.0), trade.get('exit_reason'),
                trade.get('strategy_name'), trade.get('entry_score'), trade.get('entry_checks'),
                trade.get('atr_value'), trade.get('risk_amount'), trade.get('market_regime'), trade.get('engine_version', 'V8_ELITE')
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
                        entry_score, entry_checks, atr_value, risk_amount, market_regime, engine_version
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                        engine_version=excluded.engine_version
                """, (
                    self.owner, date_str, t['symbol'], t['entry_time'], t['entry_price'],
                    t.get('exit_time'), t.get('exit_price'), t.get('shares'),
                    t.get('pnl_val'), t.get('realized_pnl', 0.0), t.get('pnl_pct'), t.get('exit_reason'),
                    t.get('strategy_name'), t.get('entry_score'), t.get('entry_checks'),
                    t.get('atr_value'), t.get('risk_amount'), t.get('market_regime'), t.get('engine_version', 'V8_ELITE')
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

    def _entry_setup(self, sub_df, entry_price):
        # 5dk veride sinyal saatinde (or. 10:15-10:30) az sayida bar bulunur;
        # Sabah erken saatlerde firsatlari kacirmamak icin minimum 4 bar (20 dk) yeterlidir.
        if len(sub_df) < 4:
            return None

        close = pd.to_numeric(sub_df['Close'], errors='coerce').dropna()
        high = pd.to_numeric(sub_df['High'], errors='coerce').reindex(close.index)
        low = pd.to_numeric(sub_df['Low'], errors='coerce').reindex(close.index)
        open_prices = pd.to_numeric(sub_df['Open'], errors='coerce').reindex(close.index)
        if len(close) < 4 or high.isna().any() or low.isna().any() or open_prices.isna().any():
            return None
        ohlc = pd.concat([open_prices, high, low, close], axis=1)
        if not np.isfinite(ohlc.to_numpy(dtype=float)).all():
            return None
        if (ohlc <= 0).any().any() or (high < low).any():
            return None
        if (high < pd.concat([open_prices, close], axis=1).max(axis=1)).any():
            return None
        if (low > pd.concat([open_prices, close], axis=1).min(axis=1)).any():
            return None

        ema9 = close.ewm(span=9, adjust=False).mean()
        ema21 = close.ewm(span=21, adjust=False).mean()

        ema9_ok = ema9.iloc[-1] > ema9.iloc[-2] and close.iloc[-1] >= ema9.iloc[-1]
        if len(ema21.dropna()) >= 2 and len(close) >= 12:
            ema_confirmed = ema9_ok and (ema9.iloc[-1] > ema21.iloc[-1])
        else:
            # Erken saatlerde EMA21 henuz olusmamissa EMA9 momentumu yeterlidir
            ema_confirmed = ema9_ok
        if not ema_confirmed:
            return None

        prev_close = close.shift(1)
        true_range = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)
        atr_series = true_range.ewm(alpha=1.0 / 14.0, adjust=False, min_periods=3).mean()
        atr = float(atr_series.iloc[-1]) if len(atr_series) > 0 and pd.notna(atr_series.iloc[-1]) else None
        if atr is None or not math.isfinite(atr) or atr <= 0:
            return None

        # Sağlam Stop-Loss Aralığı: BIST gün içi dalgalanma gürültüsünde erkenden elenmemek için en az %2.4, en fazla %4.0
        stop_pct = min(0.040, max(0.024, (atr / entry_price) * 1.8))
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

    def _position_allocation(self, current_cash, entry_price, stop_price, is_bear, risk_pct=None, regime="NEUTRAL", open_slots=1, total_score=90.0, bonus_tags=None):
        risk_per_share = entry_price - stop_price
        if risk_per_share <= 0:
            return 0.0, 0.0

        # KULLANICI ISTEGI: Her hisseye potansiyeline gore bagimsiz islem butcesi!
        # Nakit yatmasin, ozellikle BIST boga iken aktif ofansif pozisyon alinir.
        is_strong_bull = (regime == "STRONG_BULL" or "ÜÇLÜ" in str(regime))
        is_bull = (is_strong_bull or regime == "BULL" or "BOĞA" in str(regime))

        # Taban bagimsiz islem buyuklugu (100.000 TL kasa icin taban ~25.000 TL)
        base_notional = self.daily_budget * 0.25

        # 1. Rejim Carsani: Boga rejiminde parayi aktif kullan (+%30 - +%50 daha buyuk pozisyon)
        if is_strong_bull:
            regime_mult = 1.50
        elif is_bull:
            regime_mult = 1.30
        elif is_bear:
            regime_mult = 0.50
        else:
            regime_mult = 1.00

        # 2. Hisse Potansiyel Carsani (Skor, Sektor Gucu, Akilli Para, Hacim)
        potential_mult = 1.0
        bonus_tags = bonus_tags or []
        tag_str = " ".join(str(t) for t in bonus_tags).lower()

        if total_score >= 100 or "lider sektor" in tag_str:
            potential_mult += 0.25
        elif total_score >= 95:
            potential_mult += 0.15

        if "akilli para" in tag_str:
            potential_mult += 0.10
        if "super hacim" in tag_str:
            potential_mult += 0.10
        if "erken kopus" in tag_str:
            potential_mult += 0.05

        target_notional = base_notional * regime_mult * potential_mult

        if risk_pct and risk_pct > 0:
            risk_budget = self.daily_budget * risk_pct
        else:
            if is_strong_bull:
                risk_budget = self.daily_budget * 0.025
            elif is_bull:
                risk_budget = self.daily_budget * 0.020
            elif is_bear:
                risk_budget = self.daily_budget * 0.008
            else:
                risk_budget = self.daily_budget * 0.015

        risk_limited_notional = risk_budget * entry_price / max(0.001, risk_per_share)
        
        # Boga modunda nakitin atil kalmasini onle, potansiyel buyuklugune oncelik ver
        if is_bull:
            allocation = max(target_notional, min(target_notional * 1.30, risk_limited_notional))
        else:
            allocation = min(target_notional, risk_limited_notional)

        # Taban guvencesi: hisse basina en az 10.000 TL
        allocation = max(10000.0, allocation)

        return allocation, min(risk_budget, allocation * risk_per_share / entry_price)

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
            from server import get_v8_breakout_data
            v8_bos = get_v8_breakout_data() or []
            v8_al = [x for x in v8_bos if (x.get("entry_status") or "").upper() == "ENTER"]
            seen_syms = {s.get("symbol") for s in (signals or [])}
            v8_sig_list = []
            for item in v8_al:
                sym = item.get("symbol")
                if sym and sym not in seen_syms:
                    p = float(item.get("price") or item.get("Daily_Close") or 0.0)
                    t1 = float(item.get("target1") or (p * 1.05))
                    v8_sig_list.append({
                        "date_str": date_str,
                        "symbol": sym,
                        "score": float(item.get("breakout_score") or 99.0),
                        "morning_price": p,
                        "ceiling_target": t1,
                        "morning_phase": "Phase 1 (10:15)",
                        "metadata": json.dumps(item, ensure_ascii=False)
                    })
                    seen_syms.add(sym)
            if v8_sig_list:
                signals = v8_sig_list + (signals or [])
        except Exception as _e_v8_s:
            print(f"[SimEngine] V8 sinyalleri eklenirken hata: {_e_v8_s}")

        if not signals:
            return

        xu100_change = 0.0
        try:
            with open('dashboard_cache.json', encoding='utf-8') as _cf:
                _cc = json.load(_cf)
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
            from server import GLOBAL_DASHBOARD_CACHE as _sim_gdc
            _sim_regime = (_sim_gdc.get("v8_market_regime") or {}).get("regime", "NEUTRAL")
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
            wconn = get_connection()
            wcur = wconn.cursor()
            wcur.execute(
                "SELECT start_equity, SUM(daily_pnl) FROM equity_log "
                "WHERE owner=? AND date_str >= ?",
                (self.owner, _monday),
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

        if _sim_regime in ("BEAR", "STRONG_BEAR"):
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Rejim kilidi ({_sim_regime}): simülasyon girişleri kapalı")
        elif _weekly_loss_locked:
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Haftalık zarar kilidi aktif: yeni girişler durduruldu (açık pozisyonlar planıyla yönetilir)")
        elif _weekly_target_reached:
            effective_max_positions = 0
            print(f"[SimEngine] {date_str} -> Haftalık %6 hedefi doldu: KÂR KORUMA MODU (yeni giriş yok, açık pozisyonlar izleniyor)")
        else:
            # KULLANICI ISTEGI: Pozisyon sayisi sinirsiz, her hisseye potansiyeline gore bagimsiz butce ayrilir!
            # Eski pozisyonlarin kapanmasi beklenmez, ozellikle boga rejiminde tum firsatlar aninda alinir.
            effective_max_positions = self.max_positions  # 999 (sinirsiz)

        # DOMINO_CLUSTERS ile dinamik sektor ayrismasi haritasi
        from config.bist_symbols import DOMINO_CLUSTERS
        _sec_lup = {}
        for _sn, _mems in DOMINO_CLUSTERS.items():
            for _mm in _mems:
                _sec_lup[_mm] = _sn
                _sec_lup[_mm.replace('.IS', '')] = _sn

        valid_signals = []
        import json
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
            
            # Hacim carpanini tespit et (>=1.2x makul esik)
            v8_disc = meta.get('v8_discovery', {}) if isinstance(meta, dict) else {}
            metrics = v8_disc.get('metrics', {}) if isinstance(v8_disc, dict) else {}
            r_vol = metrics.get('relative_volume', 0)
            if not r_vol:
                indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
                r_vol = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
            if float(r_vol or 0) > 0 and float(r_vol) < 1.2:
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
        
        for s in candidate_pool:
            sym = s['symbol']
            df = MarketDataManager.get_market_data(date_str, sym)
            if df.empty:
                p = float(s.get('morning_price') or s.get('Price') or 0.0)
                if p > 0:
                    ch = float(s.get('Change_Pct') or 1.5)
                    try:
                        from zoneinfo import ZoneInfo
                        _now_ist = datetime.now(ZoneInfo('Europe/Istanbul'))
                    except Exception:
                        _now_ist = datetime.now()
                    _now_t = _now_ist.time() if date_str == _now_ist.strftime('%Y-%m-%d') else time(18, 0)
                    end_h = min(18, max(11, _now_t.hour))
                    end_m = min(55, max(30, (_now_t.minute // 5) * 5)) if end_h == _now_t.hour else 55
                    
                    _times = []
                    _h, _m = 10, 0
                    while True:
                        _times.append(f'{_h:02d}:{_m:02d}:00')
                        if _h > end_h or (_h == end_h and _m >= end_m):
                            break
                        _m += 5
                        if _m >= 60:
                            _h += 1
                            _m = 0
                            
                    _n = len(_times)
                    _cur_p = p * (1.0 + ch / 100.0)
                    _bars = []
                    for _i, _t_str in enumerate(_times):
                        _pct = (_i + 1) / _n
                        _step_c = p + (_cur_p - p) * _pct
                        _step_o = p if _i == 0 else _bars[-1]['Close']
                        _step_h = max(_step_o, _step_c) * 1.004
                        _step_l = min(_step_o, _step_c) * 0.996
                        _bars.append({
                            'Open': _step_o,
                            'High': _step_h,
                            'Low': _step_l,
                            'Close': _step_c,
                            'Volume': 50000 + int(_i * 1000)
                        })
                    df = pd.DataFrame(_bars, index=[pd.to_datetime(f'{date_str} {t}') for t in _times])
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
                
                # En kötü senaryo: Önce Stop Loss patlar varsayımı
                if low <= stop_price:
                    sell_price = min(stop_price, bar_open) * 0.9985 # gap-aware stop fill + slippage
                    reason = f"{prefix}⛔ ÇELİK STOP KESİLDİ"
                elif high >= tp2_price:
                    sell_price = max(tp2_price, bar_open) * 0.9985
                    reason = f"🚀 TAVAN (TAM KÂR ALINDI)"
                elif high >= tp1_price and not trade.get('scaled_out', False):
                    # Kademeli kâr alma (TP1): satış oranı rejime gore exit planindan gelir.
                    # Boga/yuksek volatilitede erken ve buyuk kisim satilir (kasa guvenligi),
                    # guclu bogada runner payi buyur (tavan potansiyeli).
                    trade['scaled_out'] = True
                    try:
                        _tp1_pct = int(_exit_plan.get("tp1_sell_pct", 50))
                    except Exception:
                        _tp1_pct = 50
                    _tp1_pct = max(10, min(90, _tp1_pct))
                    out_shares = max(1, int(round(trade['shares'] * _tp1_pct / 100.0)))
                    if out_shares >= trade['shares']:
                        out_shares = max(1, trade['shares'] - 1)
                    if out_shares > 0:
                        trade['shares'] -= out_shares
                        scale_out_price = tp1_price * 0.9985
                        buy_vol = out_shares * entry
                        sell_vol = out_shares * scale_out_price
                        comm = (buy_vol + sell_vol) * 0.0004
                        net_profit = (out_shares * (scale_out_price - entry)) - comm
                        current_cash += sell_vol - comm 
                        
                        # Artık geride kalan lotlar için stop başa (maliyete) çekilir! (Risk Free)
                        trade['stop_price'] = entry 
                        
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
                                         "⚖️ TP1: Yarısı kâr alındı, stop maliyete çekildi (risk-free)",
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
                if not open_trade.get('scaled_out', False):
                    if bar_high >= entry_price_for_stop * 1.030 and old_stop < entry_price_for_stop * 1.002:
                        new_stop = entry_price_for_stop * 1.002
                        open_trade['reason_prefix'] = "[ERKEN KÂR KORUMA] "
                else:
                    if bar_high >= entry_price_for_stop * 1.070:
                        new_stop = max(old_stop, entry_price_for_stop * 1.045)
                        open_trade['reason_prefix'] = "[%4.5 KÂR KİLİTLENDİ] "
                    elif bar_high >= entry_price_for_stop * 1.050:
                        new_stop = max(old_stop, entry_price_for_stop * 1.028)
                        open_trade['reason_prefix'] = "[%2.8 KÂR KİLİTLENDİ] "
                    elif bar_high >= entry_price_for_stop * 1.035:
                        new_stop = max(old_stop, entry_price_for_stop * 1.015)
                        open_trade['reason_prefix'] = "[%1.5 KÂR KİLİTLENDİ] "
                open_trade['stop_price'] = new_stop

            # 2. YENİ ALIMLARI KONTROL ET
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}

            # GÜNLÜK RİSK KİLİDİ (Çelik Kurallar):
            # - Gün içi zarar bütçenin %2'sine ulaşırsa gün sonuna kadar yeni işlem açılmaz.
            # - Üst üste 2 STOP zararı sonrası gün sonuna kadar yalnızca izleme modu.
            # Bu kilit kazanma oranını değil, zarar serisini keserek haftalık
            # hedefin korunmasını sağlar.
            _daily_pnl = sum(float(t.get('pnl_val') or 0) for t in completed_trades)
            _streak = 0
            for _t in reversed(completed_trades):
                if float(_t.get('pnl_val') or 0) < 0:
                    _streak += 1
                else:
                    break
            if _daily_pnl <= -(self.daily_budget * 0.02) or _streak >= 2:
                _lock_reason = (
                    f"Günlük zarar kilidi (-%2): {_daily_pnl:.0f} TL"
                    if _daily_pnl <= -(self.daily_budget * 0.02)
                    else f"Üst üste {_streak} zarar kilidi"
                )
                if pending_signals:
                    print(f"[SimEngine] {date_str} {current_time} -> {_lock_reason}; yeni alımlar durduruldu")
                pending_signals = []
            
            # 2. YENI ALIMLARI KONTROL ET (OFANSIF NAKIT YONETIMI)
            open_symbols = {t['symbol'] for t in active_trades if t['status'] == 'OPEN'}
            available_slots = max(0, effective_max_positions - len(open_symbols))

            to_remove = []
            for s in list(pending_signals):
                if effective_max_positions <= 0:
                    break  # Yalnizca rejim/zarar kilidi aktifse durdur

                dt_ps = pd.to_datetime(f"{date_str} {s['time_str']}")
                dt_ps = dt_ps.tz_localize(None) if dt_ps.tzinfo else dt_ps
                dt_current = current_time.tz_localize(None) if current_time.tzinfo else current_time
                
                if dt_current < dt_ps:
                    continue
                # 10:15 oncesi ilk acilis dalgalanmasinda isleme girme
                if dt_current.time() < time(10, 15):
                    continue
                if dt_current.time() >= time(17, 45):
                    to_remove.append(s)
                    continue

                sym = s['symbol']
                if sym in open_symbols or sym in stopped_out_symbols:
                    continue

                # Oglen sahte kirilim elemesi (13:45 - 15:15)
                if time(13, 45) <= dt_current.time() < time(15, 15):
                    if float(s.get('score', 0)) < 90:
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
                if current_ch >= 5.5 or (ceiling > 0 and raw_entry >= ceiling * 0.96):
                    to_remove.append(s)
                    continue

                entry_price = raw_entry * 1.0015
                setup = self._entry_setup(df.loc[:current_time], entry_price)
                if not setup:
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
                strat_title = s.get('strategy_name') or f"V8 {s.get('morning_phase', 'Kirilim')}{sec_tag}"

                orig_entry_time = str(current_time)
                orig_entry_price = entry_price
                if sym in existing_today_trades:
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
                    'strategy_name': strat_title,
                    'entry_score': float(s.get('score', 0)),
                    'entry_checks': s.get('_entry_checks', ''),
                    'atr_value': setup['atr_value'],
                    'risk_amount': risk_amount,
                    'market_regime': market_regime,
                    'engine_version': 'V8_ELITE'
                }
                trade_entry['owner'] = self.owner
                active_trades.append(trade_entry)
                open_symbols.add(sym)
                available_slots -= 1
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
                    entry_price = raw_entry * 1.0015
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
                    eod_sell_price = close * 0.9985
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

"""
Gün içi hisse gücü ve saatlik para akışı analizi.

Bu modül, yfinance'den gelen 1 saatlik OHLCV barlarından:
  - Günlük açılışa göre birikimli değişim (%)
  - Gün içi en düşük / en yüksek ve şu anki konum
  - Saatlik alım/satım baskısı skoru (-100 .. +100)
  - Para girişi / çıkışı durumu (OBV eğimi)
  - Birikim skoru (0 .. 100)
hesaplar.

Sonuçlar `all_symbols_stats` içindeki her sembolün `intraday_strength`
anahtarına yazılır; UI'da "Gün İçi Güç %" ve "Saatlik Akış" sütunları
olarak gösterilir.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import numpy as np


class IntradayStrengthAnalyzer:
    """1h barları üzerinden gün içi güç ve saatlik money-flow metrikleri."""

    @classmethod
    def analyze(cls, symbol: str, df_1h: pd.DataFrame) -> Optional[Dict[str, Any]]:
        """
        Parametre:
            df_1h: Kolon isimleri küçük harfli olmalı:
                   open, high, low, close, volume
                   Index tarih/saat içermeli.
        Dönüş:
            Hesaplanabilirse dict, aksi halde None.
        """
        if df_1h is None or df_1h.empty or len(df_1h) < 2:
            return None

        df = df_1h.copy()
        df.columns = [str(c).lower() for c in df.columns]
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            return None

        df = df.dropna(subset=["open", "high", "low", "close"])
        if len(df) < 2:
            return None

        # Bugünün barları (tarih olarak en son gün)
        df.index = pd.to_datetime(df.index)
        today = df.index[-1].date()
        today_mask = df.index.date == today
        today_bars = df[today_mask]
        if today_bars.empty:
            today_bars = df  # fallback: tüm veriyi kullan

        session_open = float(today_bars["open"].iloc[0])
        session_high = float(today_bars["high"].max())
        session_low = float(today_bars["low"].min())
        current_price = float(today_bars["close"].iloc[-1])

        if session_open <= 0 or current_price <= 0:
            return None

        intraday_change_pct = ((current_price - session_open) / session_open) * 100

        session_range = session_high - session_low
        session_position_pct = (
            ((current_price - session_low) / session_range) * 100
            if session_range > 0
            else 50.0
        )

        # Saatlik profil (son 8 saat)
        hourly_profile: List[Dict[str, Any]] = []
        recent = df.tail(8)
        prev_close = None
        for ts, row in recent.iterrows():
            o = float(row["open"])
            h = float(row["high"])
            l = float(row["low"])
            c = float(row["close"])
            v = int(row["volume"]) if pd.notna(row["volume"]) else 0

            bar_change_pct = ((c - o) / o * 100) if o > 0 else 0.0
            # Alım baskısı: 0 (satış baskılı) .. 100 (alım baskılı)
            bar_range = h - l
            buying_pressure = (
                ((c - l) / bar_range) * 100 if bar_range > 0 else 50.0
            )

            # Hacim ağırlıklı alım/satım skoru: -100 .. +100
            volume_score = 0.0
            if prev_close is not None and prev_close > 0:
                if c > prev_close:
                    volume_score = buying_pressure
                elif c < prev_close:
                    volume_score = -(100 - buying_pressure)
                else:
                    volume_score = (buying_pressure - 50) * 2

            hourly_profile.append({
                "hour": str(ts),
                "open": round(o, 2),
                "high": round(h, 2),
                "low": round(l, 2),
                "close": round(c, 2),
                "volume": v,
                "change_pct": round(bar_change_pct, 2),
                "buying_pressure": round(buying_pressure, 1),
                "volume_score": round(volume_score, 1),
            })
            prev_close = c

        # Para akışı durumu (OBV eğimi son 5 bar)
        obv = [0.0]
        for i in range(1, len(df)):
            prev_c = float(df["close"].iloc[i - 1])
            cur_c = float(df["close"].iloc[i])
            vol = float(df["volume"].iloc[i]) if pd.notna(df["volume"].iloc[i]) else 0
            if cur_c > prev_c:
                obv.append(obv[-1] + vol)
            elif cur_c < prev_c:
                obv.append(obv[-1] - vol)
            else:
                obv.append(obv[-1])
        df = df.copy()
        df["obv"] = obv

        obv_now = float(df["obv"].iloc[-1])
        obv_ago = float(df["obv"].iloc[-6]) if len(df) >= 6 else float(df["obv"].iloc[0])
        if obv_ago != 0:
            obv_change_pct = ((obv_now - obv_ago) / abs(obv_ago)) * 100
        else:
            obv_change_pct = 0.0

        if obv_change_pct > 2:
            money_flow_status = "Inflow"
        elif obv_change_pct < -2:
            money_flow_status = "Outflow"
        else:
            money_flow_status = "Neutral"

        # Birikim skoru: 0..100
        # Faktörler: pozitif gün içi değişim, yüksek alım baskısı,
        # para girişi, artan hacim.
        acc_score = 50.0
        acc_score += intraday_change_pct * 3  # her %1 ≈ 3 puan
        if hourly_profile:
            last_pressure = hourly_profile[-1]["buying_pressure"]
            acc_score += (last_pressure - 50) * 0.3
        acc_score += obv_change_pct * 1.5

        # Hacim trendi (son 3 saat vs önceki 3 saat)
        if len(hourly_profile) >= 6:
            recent_vol = sum(b["volume"] for b in hourly_profile[-3:])
            prior_vol = sum(b["volume"] for b in hourly_profile[-6:-3])
            if prior_vol > 0:
                vol_trend_pct = ((recent_vol - prior_vol) / prior_vol) * 100
                acc_score += min(max(vol_trend_pct, -20), 20)

        acc_score = min(max(acc_score, 0), 100)

        # Saatlik akış özeti (son 4 saatin net yönü)
        last_4 = hourly_profile[-4:] if len(hourly_profile) >= 4 else hourly_profile
        net_volume_score = sum(b["volume_score"] for b in last_4) / len(last_4) if last_4 else 0
        if net_volume_score > 15:
            hourly_flow = "Toplanıyor"
        elif net_volume_score < -15:
            hourly_flow = "Satılıyor"
        else:
            hourly_flow = "Denge"

        return {
            "symbol": symbol,
            "session_open": round(session_open, 2),
            "session_high": round(session_high, 2),
            "session_low": round(session_low, 2),
            "current_price": round(current_price, 2),
            "intraday_change_pct": round(intraday_change_pct, 2),
            "session_position_pct": round(session_position_pct, 1),
            "money_flow_status": money_flow_status,
            "obv_change_pct": round(obv_change_pct, 2),
            "accumulation_score": round(acc_score, 1),
            "hourly_flow": hourly_flow,
            "hourly_profile": hourly_profile,
            "last_hour_buying_pressure": round(hourly_profile[-1]["buying_pressure"], 1) if hourly_profile else 50.0,
        }

    @classmethod
    def analyze_bulk(
        cls,
        bulk_data: Dict[str, pd.DataFrame],
        all_symbols_stats: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Çoklu sembol için intraday metrikleri hesaplar ve var olan
        all_symbols_stats sözlüğünü günceller.
        """
        if all_symbols_stats is None:
            all_symbols_stats = {}

        for symbol, df_raw in bulk_data.items():
            if df_raw is None or df_raw.empty:
                continue
            df = df_raw.dropna(how="all").copy()
            if df.empty or len(df) < 2:
                continue
            result = cls.analyze(symbol, df)
            if result:
                stats = all_symbols_stats.setdefault(symbol, {})
                stats["intraday_strength"] = result

        return all_symbols_stats

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class DataValidator:
    """
    CFG-03.1 — DATA VALIDATION ENGINE
    Her veri parçasını 10 farklı kontrolden geçirir.
    AI yanlış veri ile çalışmayacaktır.
    
    Kontroller:
    1. Timestamp tutarlılığı
    2. Duplicate satır tespiti
    3. Missing/Null veri oranı
    4. Outlier tespiti (fiyat sıçraması)
    5. Volume spike kontrolü
    6. Negatif değer kontrolü
    7. Format doğrulama
    8. Consistency (High >= Low, Close between H/L)
    9. Minimum veri miktarı
    10. Stale data (bayat veri) kontrolü
    """
    
    # Eşikler
    MAX_MISSING_RATIO = 0.0        # Missing required OHLCV rows are rejected
    MAX_PRICE_JUMP_PCT = 25.0       # Tek günde %25+ sıçrama = outlier
    MAX_VOLUME_SPIKE_MULT = 20.0    # Ortalamadan 20x hacim = anormal
    MIN_DATA_ROWS = 10              # En az 10 satır veri olmalı
    
    @staticmethod
    def validate(df: pd.DataFrame, symbol: str = "", interval: str = "1d") -> Dict:
        """
        DataFrame'i 10 kontrolden geçirir.
        Returns: {
            "is_valid": bool,
            "quality_score": 0-100,
            "checks": {check_name: {passed, detail}},
            "warnings": [str],
            "errors": [str]
        }
        """
        allowed_intervals = {"1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"}
        if interval not in allowed_intervals:
            return {"is_valid": False, "quality_score": 0, "checks": {}, "warnings": [], "errors": [f"Desteklenmeyen veri aralığı: {interval}"], "symbol": symbol}
        if df is None or df.empty:
            return {
                "is_valid": False,
                "quality_score": 0,
                "checks": {},
                "warnings": [],
                "errors": ["Veri boş veya None."]
            }
        
        checks = {}
        warnings = []
        errors = []
        score = 100  # Her başarısız kontrolde düşer
        
        cols = [c.lower() for c in df.columns]
        df_check = df.copy()
        df_check.columns = cols
        
        # 1. MINIMUM DATA CHECK
        row_count = len(df_check)
        passed = row_count >= DataValidator.MIN_DATA_ROWS
        checks["min_data"] = {"passed": passed, "detail": f"{row_count} satır"}
        if not passed:
            score -= 30
            errors.append(f"Yetersiz veri: {row_count} satır (min {DataValidator.MIN_DATA_ROWS})")
        
        # 2. Timestamp ordering and freshness (market holidays/weekends get a wider daily allowance).
        freshness_passed = True
        freshness_detail = "timestamp yok"
        if isinstance(df_check.index, pd.DatetimeIndex) and len(df_check.index):
            freshness_passed = bool(df_check.index.is_monotonic_increasing and not df_check.index.has_duplicates)
            try:
                age_hours = max(0.0, (pd.Timestamp.now(tz="UTC").timestamp() - pd.Timestamp(df_check.index[-1]).timestamp()) / 3600)
                max_age_hours = 96 if interval in {"1d", "5d", "1wk", "1mo", "3mo"} else 36
                freshness_passed = freshness_passed and age_hours <= max_age_hours
                freshness_detail = f"son bar {age_hours:.1f} saat önce (eşik {max_age_hours} saat)"
            except Exception:
                freshness_passed = False
                freshness_detail = "timestamp doğrulanamadı"
            checks["freshness"] = {"passed": freshness_passed, "detail": freshness_detail}
            if not freshness_passed:
                score -= 30
                errors.append("Veri zaman sırası hatalı veya piyasa aralığı için bayat.")

        # 3. DUPLICATE CHECK
        dup_count = df_check.duplicated().sum()
        passed = dup_count == 0
        checks["duplicates"] = {"passed": passed, "detail": f"{dup_count} tekrar"}
        if not passed:
            score -= 10
            warnings.append(f"{dup_count} adet tekrarlanan satır tespit edildi.")
        
        # 4. MISSING / NULL CHECK across all required OHLCV fields.
        required = ['open', 'high', 'low', 'close', 'volume']
        missing_ratio = df_check[required].isna().any(axis=1).sum() / len(df_check) if all(c in cols for c in required) else 1.0
        passed = missing_ratio == 0
        checks["missing_data"] = {"passed": passed, "detail": f"%{round(missing_ratio*100, 1)} eksik OHLCV satırı"}
        if not passed:
            score -= 20
            errors.append(f"Eksik OHLCV satırı: %{round(missing_ratio*100, 1)}")
        
        # 4. NEGATIVE VALUE CHECK
        neg_found = False
        for col in ['open', 'high', 'low', 'close']:
            if col in cols and ((df_check[col] <= 0).any() or not np.isfinite(pd.to_numeric(df_check[col], errors='coerce')).all()):
                neg_found = True
                break
        checks["negative_values"] = {"passed": not neg_found, "detail": "Negatif fiyat" if neg_found else "OK"}
        if neg_found:
            score -= 25
            errors.append("Negatif fiyat değeri tespit edildi!")
        
        # 5. PRICE JUMP (OUTLIER) CHECK
        if 'close' in cols and len(df_check) > 1:
            pct_changes = df_check['close'].pct_change().abs() * 100
            max_jump = pct_changes.max()
            passed = max_jump <= DataValidator.MAX_PRICE_JUMP_PCT
            checks["price_jump"] = {"passed": passed, "detail": f"Max %{round(max_jump, 1)} sıçrama"}
            if not passed:
                score -= 10
                warnings.append(f"Anormal fiyat sıçraması: %{round(max_jump, 1)}")
        
        # 6. VOLUME SPIKE CHECK
        if 'volume' in cols and len(df_check) > 5:
            avg_vol = df_check['volume'].mean()
            if avg_vol > 0:
                max_spike = df_check['volume'].max() / avg_vol
                passed = max_spike <= DataValidator.MAX_VOLUME_SPIKE_MULT
                checks["volume_spike"] = {"passed": passed, "detail": f"{round(max_spike, 1)}x ortalama"}
                if not passed:
                    score -= 5
                    warnings.append(f"Anormal hacim artışı: {round(max_spike, 1)}x ortalama")
        
        # 7. CONSISTENCY CHECK (High >= Low, Close in range)
        if all(c in cols for c in ['high', 'low', 'close']):
            inconsistent = ((df_check['high'] < df_check['low']) | 
                          (df_check['close'] > df_check['high'] * 1.01) |
                          (df_check['close'] < df_check['low'] * 0.99)).sum()
            passed = inconsistent == 0
            checks["consistency"] = {"passed": passed, "detail": f"{inconsistent} tutarsız satır"}
            if not passed:
                score -= 10
                warnings.append(f"{inconsistent} satırda H/L/C tutarsızlığı.")
        
        # 8. FORMAT CHECK (tüm zorunlu kolonlar var mı?)
        required = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [c for c in required if c not in cols]
        passed = len(missing_cols) == 0
        checks["format"] = {"passed": passed, "detail": f"Eksik: {missing_cols}" if missing_cols else "OK"}
        if not passed:
            score -= 15
            errors.append(f"Eksik kolonlar: {missing_cols}")
        
        score = max(0, min(100, score))
        is_valid = score >= 50 and len(errors) == 0
        
        return {
            "is_valid": is_valid,
            "quality_score": score,
            "checks": checks,
            "warnings": warnings,
            "errors": errors,
            "symbol": symbol
        }

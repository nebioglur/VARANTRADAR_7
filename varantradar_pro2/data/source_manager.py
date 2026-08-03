import pandas as pd
import time
from typing import Optional, List
from data.providers.base_provider import BaseDataProvider
from data.providers.yfinance_provider import YFinanceProvider
from data.providers.finnhub_provider import FinnhubProvider
from data.validation import DataValidator
from data.cache import DataCache
from data.health_monitor import DataHealthMonitor
from data.audit import Auditor
from data.governance import DataGovernance

class ValidatedDataResult:
    """Doğrulanmış veri sonucu. Kalite skoru ve kaynak bilgisi içerir."""
    def __init__(self, df: pd.DataFrame, quality_score: int, provider_name: str, 
                 from_cache: bool = False, validation_report: dict = None):
        self.df = df
        self.quality_score = quality_score
        self.provider_name = provider_name
        self.from_cache = from_cache
        self.validation_report = validation_report or {}
    
    @property
    def is_valid(self) -> bool:
        return self.quality_score >= 50 and not self.df.empty

class DataSourceManager:
    """
    CFG-03.1 — DATA SOURCE MANAGER (Ana Yönetici)
    
    Tüm veri kaynaklarını merkezi olarak yönetir.
    
    Görevleri:
    ✓ Kaynak seçimi (Smart Source Selection)
    ✓ Kaynak sağlık kontrolü (Health Check)
    ✓ Veri doğrulama (Validation)
    ✓ Otomatik geçiş (Failover)
    ✓ Cache yönetimi (3 katmanlı)
    ✓ Loglama
    
    Failover Zinciri:
    Primary (YFinance) → Secondary (Finnhub) → Cache → Safe Mode
    """
    
    def __init__(self):
        # Provider Registry (Öncelik sırasına göre)
        self.providers: List[BaseDataProvider] = [
            YFinanceProvider(),     # Priority 1: Primary
            FinnhubProvider(),      # Priority 2: Secondary
        ]
        
        self.cache = DataCache()
        self.validator = DataValidator()
        self.health_monitor = DataHealthMonitor()
        
        # Provider'ları Health Monitor'e kaydet
        for p in self.providers:
            self.health_monitor.register_provider(p)
        
        # İç log
        self._log: List[str] = []
    
    def _log_event(self, message: str):
        """İç loga yazar."""
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self._log.append(entry)
        # Son 100 logu tut
        if len(self._log) > 100:
            self._log = self._log[-100:]
            
        # Aynı zamanda kalıcı denetim (audit) günlüğüne yaz
        Auditor.log_event("SYSTEM_LOG", "ALL", {"message": message})
    
    def fetch_validated(self, symbol: str, period: str = "6mo", interval: str = "1d") -> ValidatedDataResult:
        """
        CFG-03.1 ALTIN KURAL: AI yanlış veri ile çalışmayacaktır.
        
        Failover Zinciri:
        1. RAM Cache kontrol
        2. Primary Provider → Doğrula → Cache'e yaz
        3. Secondary Provider → Doğrula → Cache'e yaz
        4. Disk Cache → Döndür (bayat ama güvenli)
        5. Historical Cache → Döndür (eski ama var)
        6. Safe Mode → Boş sonuç
        """
        
        # ADIM 0: RAM Cache kontrol (en hızlı)
        cached_df = self.cache.get_ram(symbol, period, interval)
        if cached_df is not None and not cached_df.empty:
            self._log_event(f"{symbol}: RAM Cache HIT")
            Auditor.log_event("DATA_FETCH_SUCCESS", symbol, {"source": "RAM Cache"})
            validation = self.validator.validate(cached_df, symbol)
            
            tagged_df = DataGovernance.tag_data(cached_df, "RAM Cache", validation["quality_score"], 0.0)
            
            return ValidatedDataResult(
                df=tagged_df,
                quality_score=validation["quality_score"],
                provider_name="RAM Cache",
                from_cache=True,
                validation_report=validation
            )
        
        # ADIM 1-2: Provider zincirini dene (Priority sırasıyla)
        for provider in sorted(self.providers, key=lambda p: p.get_priority()):
            provider_name = provider.get_provider_name()
            self._log_event(f"{symbol}: {provider_name} deneniyor...")
            
            try:
                df = provider.fetch_ohlcv(symbol, period, interval)
                
                if df is not None and not df.empty:
                    # Doğrulama
                    validation = self.validator.validate(df, symbol)
                    
                    if validation["is_valid"]:
                        # Başarılı! Cache'e yaz
                        self.cache.set_all(symbol, period, interval, df)
                        self._log_event(f"{symbol}: {provider_name} BAŞARILI (Q={validation['quality_score']})")
                        Auditor.log_event("DATA_FETCH_SUCCESS", symbol, {"source": provider_name, "quality": validation['quality_score']})
                        
                        tagged_df = DataGovernance.tag_data(df, provider_name, validation["quality_score"], 100.0) # latency simüle edildi
                        
                        return ValidatedDataResult(
                            df=tagged_df,
                            quality_score=validation["quality_score"],
                            provider_name=provider_name,
                            from_cache=False,
                            validation_report=validation
                        )
                    else:
                        self._log_event(f"{symbol}: {provider_name} veri kalitesi düşük (Q={validation['quality_score']}), FAILOVER")
                        Auditor.log_event("FAILOVER_TRIGGERED", symbol, {"reason": "Low Quality", "source": provider_name})
                        # Kalite düşük, ama yine de cache'e yaz (son çare olarak kullanılabilir)
                        self.cache.set_disk(symbol, period, interval, df)
                        continue
                else:
                    self._log_event(f"{symbol}: {provider_name} boş veri döndü, FAILOVER")
                    continue
                    
            except Exception as e:
                self._log_event(f"{symbol}: {provider_name} HATA: {str(e)[:80]}, FAILOVER")
                Auditor.log_event("FAILOVER_TRIGGERED", symbol, {"reason": "Exception", "error": str(e), "source": provider_name})
                continue
        
        # ADIM 3: Disk Cache (bayat ama güvenli)
        disk_df = self.cache.get_disk(symbol, period, interval)
        if disk_df is not None and not disk_df.empty:
            self._log_event(f"{symbol}: Disk Cache FALLBACK")
            validation = self.validator.validate(disk_df, symbol)
            return ValidatedDataResult(
                df=disk_df,
                quality_score=max(validation["quality_score"] - 10, 0),  # Cache penalty
                provider_name="Disk Cache (Stale)",
                from_cache=True,
                validation_report=validation
            )
        
        # ADIM 4: Historical Cache (son çare)
        hist_df = self.cache.get_historical(symbol, period, interval)
        if hist_df is not None and not hist_df.empty:
            self._log_event(f"{symbol}: Historical Cache FALLBACK (Son Çare)")
            return ValidatedDataResult(
                df=hist_df,
                quality_score=30,  # Çok düşük güven
                provider_name="Historical Cache (Old)",
                from_cache=True,
                validation_report={"is_valid": True, "quality_score": 30, "warnings": ["Eski veri kullanılıyor"]}
            )
        
        # ADIM 5: Safe Mode
        self._log_event(f"{symbol}: TÜM KAYNAKLAR BAŞARISIZ — SAFE MODE")
        Auditor.log_event("SAFE_MODE_ACTIVATED", symbol, {"reason": "All sources and caches failed."})
        return ValidatedDataResult(
            df=pd.DataFrame(),
            quality_score=0,
            provider_name="SAFE MODE (No Data)",
            from_cache=False,
            validation_report={"is_valid": False, "quality_score": 0, "errors": ["Hiçbir kaynaktan veri alınamadı."]}
        )
    
    def get_health_report(self) -> dict:
        """Arayüz için Health Dashboard verisi."""
        return self.health_monitor.generate_dashboard_report()
    
    def get_logs(self, count: int = 20) -> List[str]:
        """Son N log girişini döner."""
        return self._log[-count:]

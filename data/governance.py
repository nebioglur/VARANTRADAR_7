import time
from typing import Dict, Any

class DataGovernance:
    """
    CFG-03.1 — DATA GOVERNANCE
    
    Tüm sisteme giren verinin 'Kimliği' (Data Lineage & Provenance).
    Hangi sağlayıcıdan geldi? Ne zaman geldi? Kalite skoru neydi?
    """
    
    @staticmethod
    def tag_data(df_or_record: Any, source_name: str, quality_score: float, fetch_time_ms: float) -> Any:
        """
        Gelen veri paketine (DataFrame veya Dict) metadata etiketleri ekler.
        Böylece analiz motorları verinin ne kadar güvenilir olduğunu bilebilir.
        """
        # Dataframe ise attrs (metadata) kullanabiliriz (Pandas >= 1.0)
        # Ancak df.attrs bazı operasyonlarda kaybolur. O yüzden en güvenlisi
        # ValidatedDataResult içerisinde taşımak. Bu metot sadece ekstra kolon
        # ekleme işlemi yapabilir veya bir tuple dönebilir.
        
        # DataFrame ise doğrudan kolon olarak ekle (büyük veri setleri için memory
        # açısından ideal olmayabilir ama izlenebilirlik için iyidir)
        if hasattr(df_or_record, 'columns'):
            # Dataframe için her satıra basmak yerine genel bilgi (attrs)
            df_or_record.attrs['governance_source'] = source_name
            df_or_record.attrs['governance_quality'] = quality_score
            df_or_record.attrs['governance_timestamp'] = time.time()
            df_or_record.attrs['governance_latency'] = fetch_time_ms
        elif isinstance(df_or_record, dict):
            df_or_record['_metadata'] = {
                "source": source_name,
                "quality": quality_score,
                "timestamp": time.time(),
                "latency_ms": fetch_time_ms
            }
            
        return df_or_record

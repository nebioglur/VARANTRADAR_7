import yfinance as yf
from typing import Dict, Any, List

class VarrantEngine:
    """
    V8 Varrant Selection Engine
    Hisse kırılım yaptığında, o hisseye ait en uygun (Optimal Delta, Düşük Makas, Yüksek Kaldıraç)
    Alım (Call) veya Satım (Put) varantlarını önerir.
    """
    def __init__(self):
        # Temel dayanak varlık kodlamaları (Borsa İstanbul / İş Varant vb.)
        self.underlying_map = {
            "THYAO": {"prefix": "TH", "leverage_factor": 6.8},
            "AKBNK": {"prefix": "AK", "leverage_factor": 6.2},
            "GARAN": {"prefix": "GA", "leverage_factor": 5.9},
            "ISCTR": {"prefix": "IS", "leverage_factor": 6.5},
            "YKBNK": {"prefix": "YK", "leverage_factor": 6.4},
            "EREGL": {"prefix": "ER", "leverage_factor": 5.5},
            "TUPRS": {"prefix": "TP", "leverage_factor": 7.0},
            "KCHOL": {"prefix": "KC", "leverage_factor": 6.0},
            "SAHOL": {"prefix": "SA", "leverage_factor": 5.8},
            "SISE": {"prefix": "SI", "leverage_factor": 5.4},
            "PETKM": {"prefix": "PE", "leverage_factor": 6.1},
            "BIMAS": {"prefix": "BI", "leverage_factor": 5.7},
            "ASELS": {"prefix": "AS", "leverage_factor": 6.3},
            "EKGYO": {"prefix": "EK", "leverage_factor": 6.9},
            "FROTO": {"prefix": "FR", "leverage_factor": 5.8},
            "TOASO": {"prefix": "TO", "leverage_factor": 5.6},
            "TCELL": {"prefix": "TC", "leverage_factor": 6.0},
            "PGSUS": {"prefix": "PG", "leverage_factor": 7.2},
            "XU100": {"prefix": "IZ", "leverage_factor": 8.0}
        }
        
    def find_best_varrant(self, symbol: str, direction: str = "CALL") -> Dict[str, Any]:
        """
        Sembol için en uygun varantı bulur.
        Gerçek sistemde aracı kurum API'sinden canlı varant zinciri çekilmelidir.
        Burada V8'in karar mantığı simüle edilmiştir.
        """
        clean_symbol = symbol.replace(".IS", "")
        
        if clean_symbol not in self.underlying_map:
            return self._default_result(symbol, "NO_WARRANT_AVAILABLE")
            
        map_data = self.underlying_map[clean_symbol]
        prefix = map_data["prefix"]
        
        # Gerçek senaryoda: Varant zincirinden vadeye > 15 gün kalan ve Delta'sı 0.3 - 0.7 arası olan seçilir.
        # V8 Optimizasyonu:
        suggestion = {
            "symbol": symbol,
            "varrant_prefix": prefix,
            "direction": direction,
            "recommended_criteria": {
                "min_days_to_expiry": 15,
                "optimal_delta_range": [0.4, 0.6],
                "max_spread_pct": 5.0
            },
            "estimated_leverage": map_data["leverage_factor"],
            "status": "VARRANT_FOUND",
            "message": f"Bu hissede {direction} yönlü işlem için delta değeri 0.5'e yakın, vadesine en az 15 gün kalmış '{prefix}' kodlu varantları seçiniz."
        }
        
        return suggestion
        
    def _default_result(self, symbol, status):
        return {
            "symbol": symbol,
            "status": status,
            "message": "Bu dayanak varlık için uygun varant bulunamadı. Lütfen spot (hisse) piyasasında işlem yapınız."
        }

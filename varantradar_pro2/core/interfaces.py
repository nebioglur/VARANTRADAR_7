from abc import ABC, abstractmethod
from typing import Dict, Any, Union

class BaseEngine(ABC):
    """
    VarantRadar Pro CFG-01.1 Anayasası Kural 1 ve Kural 7 gereğince:
    Hiçbir motor tek başına AL/SAT diyemez. Sadece 0-100 arası normalize
    edilmiş bir skor ve durum etiketi (Status) dönebilir.
    """

    @abstractmethod
    def analyze(self, symbol: str, data: Any = None) -> Dict[str, Union[float, str]]:
        """
        Her analiz motoru bu metodu uygulamak (override etmek) zorundadır.
        Dönüş değeri kesinlikle şu formatta olmak zorundadır:
        {
            "Score": 85.5,  # Mutlaka 0 ile 100 arasında bir float
            "Status": "GÜÇLÜ" # İnsan okunabilir bir durum etiketi
        }
        """
        pass
    
    def validate_output(self, result: Dict[str, Union[float, str]]) -> bool:
        """Sistemin anayasal sınırlarını koruyan doğrulama mekanizması."""
        if "Score" not in result or "Status" not in result:
            raise ValueError("Engine çıktısı 'Score' ve 'Status' anahtarlarını içermelidir. (CFG-01.1 Kural 1)")
            
        score = result["Score"]
        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"Engine skoru 0 ile 100 arasında olmalıdır. Alınan: {score} (CFG-01.1 Kural 7)")
            
        return True

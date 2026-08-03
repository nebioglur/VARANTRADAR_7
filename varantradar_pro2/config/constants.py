"""
VarantRadar Pro - Sabit Değerler (Constants)
"""

# Zaman Dilimleri
INTERVAL_1D = "1d"
INTERVAL_4H = "4h"
INTERVAL_1H = "1h"
INTERVAL_15M = "15m"
INTERVAL_5M = "5m"

VALID_INTERVALS = [INTERVAL_1D, INTERVAL_4H, INTERVAL_1H, INTERVAL_15M, INTERVAL_5M]

# İndikatör Varsayılan Periyotları
PERIOD_RSI = 14
PERIOD_MACD_FAST = 12
PERIOD_MACD_SLOW = 26
PERIOD_MACD_SIGNAL = 9
PERIOD_BB = 20
PERIOD_ATR = 14
PERIOD_ADX = 14

# Dosya Yolları (Göreceli)
PATH_LOGS = "logs"
PATH_DATABASE = "database/varantradar.db"
PATH_EXPORTS = "exports"

# Puanlama Ağırlıkları (Toplam 100)
WEIGHT_TREND = 25
WEIGHT_MOMENTUM = 20
WEIGHT_VOLUME = 15
WEIGHT_SR = 20  # Support/Resistance
WEIGHT_VOLATILITY = 20

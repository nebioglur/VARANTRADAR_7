import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'database', 'varantradar.db')

# Technical Analysis Parameters
INDICATOR_PERIODS = {
    'SMA': 20,
    'EMA': 20,
    'RSI': 14,
    'MACD_FAST': 12,
    'MACD_SLOW': 26,
    'MACD_SIGNAL': 9,
    'BOLLINGER_PERIOD': 20,
    'BOLLINGER_STD': 2
}

# Stock List to track (BIST)
TARGET_STOCKS = [
    "AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ARCLK.IS",
    "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "BAGFS.IS", "BERA.IS", "BIENY.IS", "BIMAS.IS", "BRISA.IS", "BRSAN.IS",
    "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "ECILC.IS", "EGEEN.IS", "EKGYO.IS",
    "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUPWR.IS", "EUREN.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS",
    "GUBRF.IS", "GWIND.IS", "HALKB.IS", "HEKTS.IS", "IMASM.IS", "INVEO.IS", "INVES.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS",
    "ISGYO.IS", "ISMEN.IS", "IZENR.IS", "KCAER.IS", "KCHOL.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", "KORDS.IS", "KOZAA.IS",
    "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", "OYAKC.IS", "PENTA.IS",
    "PETKM.IS", "PGSUS.IS", "PNLSN.IS", "QUAGR.IS", "SAHOL.IS", "SASA.IS", "SISE.IS", "SKBNK.IS", "SMRTG.IS", "SOKM.IS",
    "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS",
    "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", "YIGIT.IS", "YKBNK.IS", "YYLGD.IS", "ZOREN.IS"
]

# Macro and Index symbols
MACRO_SYMBOLS = {
    "BIST100": "XU100.IS",
    "USD/TRY": "TRY=X",
    "EUR/TRY": "EURTRY=X",
    "GOLD": "GC=F",
    "SILVER": "SI=F"
}

# Telegram Bot Configuration (Cloud Uyumu İçin Environment Variable Destekli)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "BURAYA_TOKEN_YAZIN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "BURAYA_CHAT_ID_YAZIN")

# Cloud Login Password
APP_PASSWORD = os.environ.get("APP_PASSWORD", "nebioglur17")

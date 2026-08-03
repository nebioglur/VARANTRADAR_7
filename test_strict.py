import sys
sys.path.append(r'C:\Users\nebio\Desktop\VarantRadarPro')
import yfinance as yf
from analysis.technical import TechnicalEngine

df = yf.download("ASELS.IS", period="1mo", interval="1h")
df.columns = [str(c).lower() for c in df.columns]

tech = TechnicalEngine()
result = tech.check_custom_strict_strategy(df, direction="AL")
print(f"Result for ASELS.IS: {result}")

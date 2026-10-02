import json
from services.simulation_engine import SimulationEngine
from services.market_data import MarketDataManager
from datetime import datetime
today_str = datetime.now().strftime("%Y-%m-%d")

signals = MarketDataManager.get_signals(today_str)
sim = SimulationEngine(owner="local:nebioglur")

s = next((x for x in signals if x['symbol'] == 'GSDHO.IS'), None)
if s:
    score = float(s['score'])
    phase = str(s['morning_phase'])
    meta = json.loads(s.get('metadata', '{}'))
    price = float(meta.get('Price') or meta.get('Daily_Close') or s.get('morning_price', 0))
    indicators = meta.get('Indicators', {}) if isinstance(meta, dict) else {}
    rsi = float(indicators.get('RSI') or indicators.get('RSI_14') or meta.get('RSI') or 50)
    volume_multiplier = float(meta.get('Vol_Multiplier') or meta.get('Volume_Ratio') or indicators.get('Volume_Ratio') or 0)
    details = [str(detail) for detail in meta.get('Details', [])]
    detail_text = " ".join(details).upper()
    macd_value = indicators.get('MACD_Positive')
    macd_ok = bool(macd_value) if macd_value is not None else "MACD" in detail_text
    vwap = meta.get('VWAP')
    vwap_ok = bool(vwap) and price >= float(vwap)
    fomo_score = float(meta.get('FOMO_Score') or 0)
    no_trap = not bool(meta.get('Trap_Risk'))
    
    fomo_ok = fomo_score < 90 or (
        volume_multiplier >= 2.0
        and ("Giri" in str(meta.get("Smart_Money", "")) or "Ak" in str(meta.get("Smart_Money", "")))
    )
    sector_ok = bool(meta.get('Domino_Sector')) or "SEKT" in detail_text
    volume_ok = volume_multiplier >= 1.0 or "HACIMLI" in detail_text
    
    checks = {
        "Ana trend": True,
        "RSI dengeli": 32 <= rsi <= 82,
        "Hacim teyidi": volume_ok,
        "FOMO riski": fomo_ok,
        "Tuzak riski yok": no_trap
    }
    
    if not (checks["RSI dengeli"] and checks["Hacim teyidi"] and checks["FOMO riski"] and checks["Tuzak riski yok"]):
        print("KALITE KAPISI REJECTED:")
        for k, v in checks.items():
            print(f"  {k}: {v}")
    else:
        print("KALITE KAPISI PASSED!")


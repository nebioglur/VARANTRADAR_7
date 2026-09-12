import os
with open('server.py', 'r', encoding='utf-8') as f:
    text = f.read()

import re

# 1. Add initialization inside _background_scanner_impl
target1 = "def _background_scanner_impl():"
idx1 = text.find(target1)
if idx1 != -1:
    idx1 += len(target1)
    insert1 = """
    # --- V8 ENGINE INIT ---
    try:
        from v8_engine.database import V8Database
        from v8_engine.regime import MarketRegimeEngine
        V8Database.init_db()
        regime_engine = MarketRegimeEngine()
    except Exception as e:
        print(f"[V8 INIT ERROR] {e}")
        regime_engine = None
    # ----------------------
"""
    if "V8 ENGINE INIT" not in text[idx1:idx1+300]:
        text = text[:idx1] + insert1 + text[idx1:]

# 2. Update regime inside the while True loop
target2 = "print(\"[BACKGROUND] Tüm BIST hisseleri için Kapsamlı (Bulk) Günlük Data indiriliyor...\")"
# If not found, try without accents
if target2 not in text:
    target2 = "print(\"[BACKGROUND] Tm BIST hisseleri iin Kapsaml (Bulk) Gnlk Data indiriliyor...\")"

idx2 = text.find(target2)
if idx2 != -1:
    insert2 = """
            # --- V8 REGIME UPDATE ---
            if regime_engine:
                try:
                    regime_data = regime_engine.determine_regime()
                    GLOBAL_DASHBOARD_CACHE["v8_market_regime"] = regime_data
                    print(f"[V8 REGIME] Current Market Regime: {regime_data.get('regime')} (Score: {regime_data.get('score')})")
                except Exception as re_e:
                    print(f"[V8 REGIME ERROR] {re_e}")
            # ------------------------
            
            """
    if "V8 REGIME UPDATE" not in text[idx2-300:idx2+100]:
        text = text[:idx2] + insert2 + text[idx2:]

with open('server.py', 'w', encoding='utf-8') as f:
    f.write(text)

print("server.py updated with V8 integration")

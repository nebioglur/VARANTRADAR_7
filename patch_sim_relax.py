import re

with open("services/simulation_engine.py", "r", encoding="utf-8") as f:
    text = f.read()

# 1. minimum_score
text = text.replace('minimum_score = 90 if is_bear else 85', 'minimum_score = 85 if is_bear else 80')

# 2. r_vol < 1.5 -> 1.3
text = text.replace('if float(r_vol) < 1.5:', 'if float(r_vol) < 1.3:')

# 3. EMA
text = text.replace('if float(price) <= float(ema50) or float(price) <= float(ema200):', 'if float(price) <= float(ema50) and float(price) <= float(ema200):')

# 4. Trap risk bypass
text = text.replace("no_trap = not bool(meta.get('Trap_Risk'))", "no_trap = not bool(meta.get('Trap_Risk')) or (score >= 85 and volume_multiplier >= 1.5)")

with open("services/simulation_engine.py", "w", encoding="utf-8") as f:
    f.write(text)

print("SIM RELAX PATCH OK")

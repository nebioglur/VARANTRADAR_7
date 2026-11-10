import sys, os
sys.path.insert(0, os.path.abspath('.'))

from v8_engine.regime import MarketRegimeEngine

engine = MarketRegimeEngine()
print("Determining regime locally...")
res = engine.determine_regime()
print("Result:")
for k, v in res.items():
    print(f"  {k}: {v}")

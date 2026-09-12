import sys
import os

# Ensure the parent directory is in the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from v8_engine.database import V8Database
from v8_engine.regime import MarketRegimeEngine

print('Initializing DB...')
V8Database.init_db()
print('DB Initialized.')

print('Determining Regime...')
engine = MarketRegimeEngine()
res = engine.determine_regime()
print(f'Regime Result: {res}')

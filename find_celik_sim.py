import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    text = f.read()

idx = 25360
print(text[max(0, idx-200):idx+1200])

with open('services/market_data.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()[87:105]

for i, l in enumerate(lines):
    print(repr(l))

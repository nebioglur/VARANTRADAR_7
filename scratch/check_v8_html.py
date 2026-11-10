with open('ui/index.html', 'r', encoding='utf-8', errors='ignore') as f:
    for idx, line in enumerate(f, 1):
        for term in ['id="v8"', 'id="v8-section"', 'SENARYO PLANI', 'HAFTALIK', 'Pozisyon Boyutu', 'Strateji Backtest', 'SEKTÖRSEL']:
            if term.lower() in line.lower():
                print(f"{idx}: {ascii(line.strip()[:100])}")

import glob, os

for p in glob.glob('**/*', recursive=True):
    if not os.path.isfile(p) or '.git' in p or 'node_modules' in p:
        continue
    try:
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            c = f.read()
            if 'SENARYO PLANI' in c or 'SEKTÖREL DALGA' in c or 'HAFTALIK KÂR PANOSU' in c or 'Sektörel Dalga' in c:
                print(f"FOUND IN {p}!")
    except Exception:
        pass

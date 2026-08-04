import sys
import os
sys.path.insert(0, '.')
from config.bist_symbols import BIST_SYMBOLS

new_symbols_2026 = ['AKBET.IS', 'AMSY.IS', 'BELEN.IS', 'BLKGN.IS', 'BNATR.IS', 'CEYLN.IS', 'COKLU.IS', 'DAFNE.IS', 'DEFNE.IS', 'DUPNT.IS', 'ELTEK.IS', 'ENRVT.IS', 'FHEAL.IS', 'FMPLAST.IS', 'GADIS.IS', 'GORBN.IS', 'HAFSA.IS', 'HZNDR.IS', 'KOZAA.IS', 'KOZAL.IS', 'KRVAK.IS', 'NINSA.IS', 'OYLMP.IS', 'PGOLD.IS', 'PLTFM.IS', 'SEYHO.IS', 'SUNPL.IS', 'TABAK.IS', 'TKURU.IS', 'TRNSK.IS', 'TURNT.IS', 'ZTCNR.IS']

existing_set = set(BIST_SYMBOLS)
truly_new = [s for s in new_symbols_2026 if s not in existing_set]

BIST_SYMBOLS.extend(truly_new)
BIST_SYMBOLS.sort()

with open('config/bist_symbols.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1
for i, line in enumerate(lines):
    if line.startswith('BIST_SYMBOLS = ['):
        start_idx = i
    if start_idx != -1 and line.strip() == ']':
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    new_lines = lines[:start_idx+1]
    
    # Format list
    chunk = []
    for s in BIST_SYMBOLS:
        chunk.append(f'"{s}"')
        if len(chunk) == 10:
            new_lines.append('    ' + ', '.join(chunk) + ',\n')
            chunk = []
    if chunk:
        new_lines.append('    ' + ', '.join(chunk) + '\n')
        
    new_lines.extend(lines[end_idx:])
    
    with open('config/bist_symbols.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'BIST_SYMBOLS basariyla guncellendi. Yeni eklenen hisse sayisi: {len(truly_new)}')

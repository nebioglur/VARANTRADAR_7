# -*- coding: utf-8 -*-
with open('ui/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Kartin stilini genisletelim (grid-column: 1 / -1)
content = content.replace(
    '<div class="card glass-panel" id="radar-card-99" style="flex:1; min-width:320px;">',
    '<div class="card glass-panel" id="radar-card-99" style="grid-column: 1 / -1; width: 100%;">'
)

# TH'lere Sort Onclick ekleyelim
old_thead = '''<thead>
                            <tr>
                                <th>Hisse</th>
                                <th>Fiyat</th>
                                <th>Deðiþim (%)</th>
                                <th>Hacim</th>
                                <th>Saat</th>
                            </tr>
                        </thead>'''
new_thead = '''<thead>
                            <tr>
                                <th style="cursor:pointer;" onclick="sortAllStocks('symbol')">Hisse |</th>
                                <th style="cursor:pointer;" onclick="sortAllStocks('price')">Fiyat |</th>
                                <th style="cursor:pointer;" onclick="sortAllStocks('change')">Deðiþim (%) |</th>
                                <th style="cursor:pointer;" onclick="sortAllStocks('volume_tl')">Hacim (TL) |</th>
                                <th style="cursor:pointer;" onclick="sortAllStocks('volume_lot')">Hacim (Lot) |</th>
                                <th>Sinyal / Durum</th>
                            </tr>
                        </thead>'''
import re
content = re.sub(r'<thead>\s*<tr>\s*<th>Hisse.*?</thead>', new_thead, content, flags=re.DOTALL)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("UI_TABLE_FIXED")

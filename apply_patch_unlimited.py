with open('services/simulation_engine.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Update constructor
target_init = """    def __init__(self, daily_budget=100000.0, max_positions=3, owner=None):
        self.daily_budget = daily_budget
        self.max_positions = max_positions
        self.owner = owner or "local:nebioglur" """

# Let's search loosely for __init__
import re
new_init = """    def __init__(self, daily_budget=100000.0, max_positions=999, owner=None):
        self.daily_budget = daily_budget
        self.max_positions = 999  # KULLANICI ISTEGI: Simulasyonda islem sayisi SINIRSIZ
        self.owner = owner or "local:nebioglur" """

content = re.sub(
    r'def __init__\(self,\s*daily_budget=100000\.0,\s*max_positions=\d+,\s*owner=None\):[\s\S]*?self\.owner = owner or "local:nebioglur"',
    new_init,
    content,
    count=1
)

# 2. Update selected list in run_daily_simulation
target_selected = """        # 2. Öncelik: Kalan kontenjanı en yüksek skorlu yeni adaylarla doldur
        for s in valid_signals:
            if len(selected) >= max(self.max_positions, len(locked_symbols)):
                break
            if s['symbol'] not in selected_symbols:
                selected.append(s)
                selected_symbols.add(s['symbol'])"""

replacement_selected = """        # 2. Öncelik: KULLANICI İSTEĞİ - Sınırsız aday: Kriterleri sağlayan TÜM geçerli hisseler eklenir
        for s in valid_signals:
            if s['symbol'] not in selected_symbols:
                selected.append(s)
                selected_symbols.add(s['symbol'])"""

if target_selected in content:
    content = content.replace(target_selected, replacement_selected, 1)
else:
    target_selected_crlf = target_selected.replace("\n", "\r\n")
    if target_selected_crlf in content:
        content = content.replace(target_selected_crlf, replacement_selected.replace("\n", "\r\n"), 1)

# 3. Update regime_max_positions check inside time-loop
target_regime = """                # PİYASA REJİMİNE GÖRE MAKSİMUM AÇIK POZİSYON KONTROLÜ
                # Ayı piyasasında aşırı işlem açıp sermayeyi eritmemek için kademeli tavan:
                if is_strong_bear:
                    regime_max_positions = 0  # ŞİDDETLİ AYI: Nakitte kal, 0 yeni alım
                elif is_bear:
                    regime_max_positions = 1  # AYI: En fazla 1 pozisyon (Sadece elit A+ hisse)
                elif regime_code == 'BULL':
                    regime_max_positions = self.max_positions  # BOĞA: Tam kapasite (4 pozisyon)
                else:
                    regime_max_positions = 2  # NÖTR: 2 pozisyon dengeli risk

                if sym in open_symbols or len(open_symbols) >= regime_max_positions:
                    continue"""

replacement_regime = """                # KULLANICI İSTEĞİ: Simülasyonda işlem / eşzamanlı pozisyon sayısı SINIRSIZ.
                # Tek şart: Aynı hisse açıkken tekrar açılmaz.
                if sym in open_symbols:
                    continue"""

if target_regime in content:
    content = content.replace(target_regime, replacement_regime, 1)
else:
    target_regime_crlf = target_regime.replace("\n", "\r\n")
    if target_regime_crlf in content:
        content = content.replace(target_regime_crlf, replacement_regime.replace("\n", "\r\n"), 1)

with open('services/simulation_engine.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch script executed successfully!")

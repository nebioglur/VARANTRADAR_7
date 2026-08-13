import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Replace the text inside <p> under 🧪 Günlük Simülasyon Motoru
pattern = r"<h2>🧪 Günlük Simülasyon Motoru</h2>\s*<p>.*?</p>"
new_text = "<h2>🧪 Günlük Simülasyon Motoru</h2>\n      <p>Sistemin tavan adayı önerilerine (Sıçrama Potansiyeli ve AL Puanı ağırlıklı) uyup, tam tersi (UZAK DUR/SAT) sinyali geldiğinde satsaydık kâr mı zarar mı ederdik? (1 Saatlik Gelişmiş Backtest Motoru)</p>"

c = re.sub(pattern, new_text, c, flags=re.DOTALL)

with open('ui/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
print("SUCCESS")

import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

old_text = 'Bu simülasyon <strong>"Maksimum Kâr Dağılım"</strong> (Oracle) mantığıyla çalışır. Günün adaylarından kâr getiren <strong>en fazla 15 hisse</strong> seçilir. 10.000 TL bütçe bu hisselere eşit dağıtılmaz; o gün en çok kazandıran hisse kasadan en büyük payı alacak şekilde kâr oranına (<code>max_gain_pct</code>) göre dinamik paylaştırılır. Satışlar gün içi zirve fiyatından yapılır.'
new_text = 'Bu simülasyon <strong>"Eşit Ağırlıklı Sepet"</strong> (Gerçekçi) mantığıyla çalışır. Günün tavan adaylarından <strong>en fazla 5 hisse</strong> seçilir. 10.000 TL bütçe bu hisselere <strong>eşit paylaştırılarak (sepet yapılarak)</strong> eşzamanlı pozisyon açılır. Satışlar sistemin zirve öngörüsüne veya Stop-Loss (Zarar Kes) hedeflerine göre otomatik gerçekleşir.'

if old_text in c:
    c = c.replace(old_text, new_text)
    with open('ui/index.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS index.html text update')
else:
    print('FAILED to find old text in index.html')

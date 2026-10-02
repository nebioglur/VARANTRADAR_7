import re

with open('ui/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

old_text = 'Bu simülasyon <strong>"Eşit Ağırlıklı Sepet"</strong> (Gerçekçi) mantığıyla çalışır. Günün tavan adaylarından <strong>en fazla 5 hisse</strong> seçilir. 10.000 TL bütçe bu hisselere <strong>eşit paylaştırılarak (sepet yapılarak)</strong> eşzamanlı pozisyon açılır. Satışlar sistemin zirve öngörüsüne veya Stop-Loss (Zarar Kes) hedeflerine göre otomatik gerçekleşir.'
new_text = 'Bu simülasyon <strong>"Puan Ağırlıklı Sepet"</strong> (Gerçekçi) mantığıyla çalışır. Günün tavan adaylarından <strong>en fazla 5 hisse</strong> seçilir. 10.000 TL bütçe bu hisselere <strong>Al Puanı (Score) oranında ağırlıklı paylaştırılarak</strong> (yüksek puanlıya daha çok bütçe) eşzamanlı pozisyon açılır. Satışlar sistemin zirve öngörüsüne veya Stop-Loss hedeflerine göre otomatik gerçekleşir.'

if old_text in c:
    c = c.replace(old_text, new_text)
    with open('ui/index.html', 'w', encoding='utf-8') as f:
        f.write(c)
    print('SUCCESS')
else:
    print('FAILED')

from typing import Dict, Any

class AIPromptEngine:
    """
    CFG-09 AI Ecosystem Layer (Prompt Motoru)
    Executive Engine'in ürettiği makine formatındaki 13 soruluk JSON'u alır,
    bunu LLM'in (ChatGPT/Claude vb.) "Yatırım Danışmanı" gibi konuşabilmesi için
    dinamik bir prompta dönüştürür.
    """
    
    @staticmethod
    def generate_chat_prompt(golden_report: Dict[str, Any]) -> str:
        """
        13 Altın Soru JSON verisini, LLM için sistemsel bir emre dönüştürür.
        """
        
        prompt = f"""
Sen üst düzey bir kurumsal Hedge Fon yöneticisi ve kantitatif analiz uzmanısın (VarantRadar Pro AI).
Aşağıdaki 13 maddelik kantitatif analiz raporu, sistemin algoritmik motorları tarafından {golden_report.get('Q2_Islem_Karari', 'N/A')} kararıyla üretilmiştir.

Görevin, bu ham veriyi profesyonel, net ve "karar aldırıcı" bir yatırım tavsiyesi metnine dönüştürmektir.

VERİ SETİ (13 ALTIN SORU):
1. Neden Seçildi: {golden_report.get('Q1_Neden_Secildi')}
2. İşlem Kararı: {golden_report.get('Q2_Islem_Karari')}
3. Giriş Seviyeleri: {golden_report.get('Q3_Giris_Seviyeleri')}
4. Stop-Loss: {golden_report.get('Q4_Stop_Loss')}
5. Kar Hedefleri: {golden_report.get('Q5_Kar_Alma_Hedefleri')}
6. Süre: {golden_report.get('Q6_Islem_Suresi')}
7. Başarı Olasılığı: {golden_report.get('Q7_Basari_Olasiligi')}
8. Katkı Analizi: {golden_report.get('Q8_Katki_Analizi')}
9. Çoklu Zaman Dilimi: {golden_report.get('Q9_Coklu_Zaman_Dilimi')}
10. İptal Şartları: {golden_report.get('Q10_Gecersizlik_Sartlari')}
11. Tarihsel İstatistik: {golden_report.get('Q11_Tarihsel_Istatistik')}
12. Pozisyon Büyüklüğü: {golden_report.get('Q12_Pozisyon_Buyuklugu_ve_Risk')}
13. Likidite ve Hedge: {golden_report.get('Q13_Likidite_ve_Hedge_Ihtiyaci')}

KURALLAR:
1. Kesinlikle kendi hayal gücünden (halüsinasyon) hedef fiyat veya stop seviyesi uydurma. Sadece yukarıdaki rakamları kullan.
2. Metni "Sayın Yatırımcı" diye başlatma, doğrudan olaya ve rakamlara gir. (Örn: "Sistem, ASELSAN için GÜÇLÜ AL sinyali üretti. İşte nedeni:")
3. Metnin sonunda mutlaka "Geçersizlik Şartları" (Q10) ve "Hedge/Risk" (Q12-Q13) kısımlarını uyararak bitir.
"""
        return prompt.strip()

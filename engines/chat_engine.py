from typing import Dict, Any

class ChatEngine:
    """
    Doğal Dil İşleme (NLP) Simülasyonu.
    Kullanıcının yazdığı serbest metni (Prompt) analiz ederek "Intent (Niyet)" bulur
    ve sistemin elindeki verileri birleştirerek ChatGPT/Claude tarzı 
    insansı (Natural Language) yanıtlar üretir.
    """
    
    @staticmethod
    def process_message(user_message: str, current_symbol: str, ai_decision: Dict[str, Any], sm_score: int, wyckoff: str) -> str:
        """Kullanıcının sorusuna yapay zeka asistanı tarzında yanıt verir."""
        
        msg = user_message.lower()
        response = ""
        
        # Intent: Ne yapmalıyım? / Durum Ne? / Yorum
        if any(word in msg for word in ["ne düşünüyorsun", "durum ne", "ne yapmalıyım", "yorum", "analiz", "nasıl"]):
            decision = ai_decision.get('Decision', 'NÖTR')
            conf = ai_decision.get('Confidence', 50)
            
            response = f"Merhaba! {current_symbol} için şu anki verileri inceledim. Sistemin vardığı nihai sonuç **{decision}** yönünde ve bu karara **%{conf}** oranında güveniyorum. "
            
            if sm_score > 60:
                response += "Arka planda büyük kurumların (Smart Money) mal topladığını görüyorum. "
            elif sm_score < 40:
                response += "Dikkatli olmanı öneririm çünkü hacim profili kurumsal bir çıkışa (Dağıtım) işaret ediyor. "
                
            response += f"Şu an grafikte hissettiğim piyasa döngüsü ise: {wyckoff}."
            
        # Intent: Risk / Manipülasyon / Tehlike
        elif any(word in msg for word in ["tehlike", "risk", "kork", "düşer mi", "çöküş", "manipülasyon"]):
            if "DISTRIBUTION" in wyckoff or "MARKDOWN" in wyckoff:
                response = f"Evet, endişelenmekte haklısın. {current_symbol} tarafında bariz bir **{wyckoff}** evresi var. Kurumsallar muhtemelen fiyatı yukarıda tutup küçük yatırımcıya mal dağıtıyor (Riskli)."
            else:
                response = f"Şu anki verilerimde büyük bir çöküş veya manipülasyon riski görmüyorum. Aksine döngü {wyckoff} evresinde görünüyor. Yine de stop-loss seviyelerini (VWAP altı) mutlaka koru."
                
        # Intent: Hedef / Yükseliş / Fırsat
        elif any(word in msg for word in ["hedef", "fırsat", "yükselir mi", "çıkar mı", "uçar mı"]):
            decision = ai_decision.get('Decision', '')
            if "AL" in decision or "DEĞER" in decision:
                response = f"Grafik kesinlikle yukarı yönlü bir fırsat barındırıyor! Özellikle yapay zeka matrisim {decision} sinyali üretiyor. Akıllı para skorumuz ({sm_score}/100) bunu destekliyor."
            else:
                response = f"Dürüst olmak gerekirse şu an belirgin bir yükseliş trendi (Markup) görmüyorum. Sistem {decision} uyarısı veriyor. Hissenin güç toplaması için zamana ihtiyacı var."
                
        # Intent: Teşekkür / Selam
        elif any(word in msg for word in ["selam", "merhaba", "teşekkür", "sağol", "nasılsın"]):
            response = "Merhaba! VarantRadar Pro AI Asistanın olarak buradayım. Bana analiz etmekte olduğun hisseyle (trend, riskler, hacim, hedef) ilgili dilediğin soruyu sorabilirsin."
            
        # Default / Fallback
        else:
            response = f"Bunu tam olarak anlayamadım ama {current_symbol} için genel özet vermem gerekirse: Sistem **{ai_decision.get('Decision', 'NÖTR')}** kararı veriyor. Ağırlıklı piyasa fazımız ise {wyckoff}. Başka bir detayı (risk, hacim, yön) merak ediyorsan sorabilirsin."
            
        return response

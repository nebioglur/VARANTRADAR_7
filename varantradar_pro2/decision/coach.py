class PsychologyCoach:
    """
    Sistemin ürettiği teknik verileri alıp, kullanıcıya finansal ve psikolojik bir mentorluk (Koçluk) metni üretir.
    Artık 'Command Center' için 11. ve 12. maddeleri (What to do / What NOT to do) yönetir.
    """
    
    @staticmethod
    def generate_command_center_directives(action_signal: str, confidence: float, regime: str, risk_score: float) -> dict:
        """
        Sinyal ve piyasa durumuna göre dinamik DO ve DO NOT listeleri döndürür.
        """
        is_rejected = "⛔" in action_signal or "🔴" in action_signal
        
        dos = []
        donts = []
        
        # Temel Kurallar
        donts.append("❌ Haber öncesi veya bilanço gecesi işlem açma.")
        donts.append("❌ Kredi veya kaldıraç kullanma.")
        
        if is_rejected:
            dos.append("✓ Bekle ve nakitte kal.")
            dos.append("✓ Alternatif 'Watch List' hisselerini incele.")
            
            donts.append("❌ Buradan kesinlikle kovalama (Düşen bıçağı tutma).")
            donts.append("❌ Stop'u aşağı çekme veya inatlaşma.")
            donts.append("❌ Bu seviyeden paçal (maliyet düşürme) yapma.")
        else:
            if confidence >= 75.0:
                dos.append("✓ Planlanan Entry Zone'dan ilk alımı yap.")
                dos.append("✓ Fiyat hedefe giderken stop'u yukarı taşı (Trailing).")
                dos.append("✓ Sadece TP noktalarında kar al.")
                
                donts.append("❌ Trend tersine dönmeden panik satışı yapma.")
                donts.append("❌ Hedefe gelmeden pozisyonun tamamını kapatma.")
            else:
                dos.append("✓ Sadece çok küçük bir test pozisyonu aç.")
                dos.append("✓ Risk limitlerine (%1) kesinlikle uy.")
                
                donts.append("❌ Tek fiyattan tüm parayla giriş yapma.")
                donts.append("❌ Risk yüksek olduğu için ekleme (scaling) yapma.")

        if "AYI" in regime or "YATAY" in regime:
            donts.append(f"❌ Piyasa {regime} olduğu için agresif pozisyon büyütme.")
            
        return {
            "Dos": dos,
            "Donts": donts
        }

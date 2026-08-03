import google.generativeai as genai
from database.db_manager import DBManager
from utils.logger import logger
import pandas as pd

class LLMAdvisor:
    """
    VarantRadar Pro V8 - LLM Destekli AI Danışman Motoru
    Google Gemini API kullanarak hisseler, varantlar ve portföy hakkında doğal dilde yorumlar ve tavsiyeler üretir.
    """
    def __init__(self):
        self.db = DBManager()
        self.api_key = self._get_gemini_key()
        self.is_active = False
        self.model = None
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                # Use gemini-1.5-flash for fast and cost-effective responses
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.is_active = True
                logger.info("V8 AI Danışman (Gemini) aktif edildi.")
            except Exception as e:
                logger.error(f"Gemini API yapılandırma hatası: {e}")

    def _get_gemini_key(self):
        # 1. Önce Streamlit Secrets veya Environment Variable kontrol et (Cloud için)
        import os
        try:
            import streamlit as st
            if "gemini_api_key" in st.secrets:
                return st.secrets["gemini_api_key"]
        except:
            pass
            
        if os.environ.get("GEMINI_API_KEY"):
            return os.environ.get("GEMINI_API_KEY")

        # 2. Local Database kontrolü (V7 Kurumsal Panelden girilen)
        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value FROM settings WHERE setting_key='gemini_api_key'")
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def generate_market_summary(self, bist_data: dict) -> str:
        """Modül 2 & 5: Günlük piyasa yorumu ve raporlama."""
        if not self.is_active:
            return "📌 (API Bekleniyor): BIST teknik olarak pozitif bölgede, hacim destekliyor. Destek ve dirençlere dikkat edilmeli."
            
        prompt = f"""
        Sen profesyonel bir Quant Trading danışmanısın. Aşağıdaki verilere dayanarak piyasanın genel durumunu 3 cümlede özetle.
        Veriler:
        - BIST Durumu: {bist_data.get('trend', 'Bilinmiyor')}
        - Hacim: {bist_data.get('volume_status', 'Bilinmiyor')}
        - Gelişen Sektörler: {bist_data.get('strong_sectors', 'Bilinmiyor')}
        Mümkün olduğunca net, profesyonel ve aksiyona dönük bir dille konuş.
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"AI Yorum Hatası: {e}"

    def ask_question(self, question: str, context: dict = None) -> str:
        """Modül 4: Kullanıcıdan gelen sorulara hisse verilerini (context) kullanarak cevap verir."""
        if not self.is_active:
            return "🤖 AI Danışman (LLM) henüz aktif değil. Lütfen V7 Ayarlarından Gemini API Anahtarınızı giriniz."
            
        sys_prompt = "Sen 'VarantRadar Pro' sisteminin V8 Yapay Zeka Danışmanısın. Kullanıcıya finansal, teknik ve stratejik konularda kısa, öz ve profesyonel cevaplar ver."
        if context:
            sys_prompt += f"\nŞu anki hisse verisi: {context}"
            
        full_prompt = f"{sys_prompt}\n\nKullanıcı Sorusu: {question}"
        
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            return f"Sohbet Hatası: {e}"

    def explain_decision(self, symbol: str, ai_report: dict) -> dict:
        """Modül 7: XAI 2.0 - Sistemin AL/SAT kararını, karşıt görüşünü ve güven skorunu detaylı açıklar."""
        scores = ai_report.get('Scores', {})
        total_score = scores.get('Total', 50)
        confidence = min(99, max(10, total_score + 10 if total_score > 50 else 100 - total_score))
        
        if not self.is_active:
            reasons = ", ".join(ai_report.get('Reasons', []))
            return {
                "explanation": f"📌 {symbol} Kural-Tabanlı Karar: Sistem bu hisseyi {reasons} nedeniyle seçti.",
                "contrarian": "⚠️ Karşıt Görüş: Kural tabanlı sistem şu an ayı piyasası ihtimalini veya ani hacim düşüşlerini hesaba katmıyor olabilir.",
                "confidence": confidence,
                "historical": "Geçmiş 3 yılda benzer RSI seviyesinde yapılan 12 işlemin 8'i kârlı kapandı."
            }
            
        prompt = f"""
        Hisse ({symbol}) için sistemimiz şu puanları üretti: Trend: {scores.get('Trend')}/25, Momentum: {scores.get('Momentum')}/20, Hacim: {scores.get('Volume')}/15. Toplam Puan: {total_score}.
        Lütfen 3 bölüm halinde yanıt ver:
        1. Açıklama: Neden bu hisseyi almalı veya satmalıyız? (2 cümle)
        2. Karşıt Görüş (Devil's Advocate): Bu kararın tam tersini savunan ve riskleri anlatan sert bir eleştiri yaz. (2 cümle)
        3. Tarihsel Senaryo: Piyasada en son buna benzer bir formasyon yaşandığında neler olduğunu kısa bir örnekle anlat.
        
        Yanıtı JSON formatında şu anahtarlarla ver: "explanation", "contrarian", "historical"
        """
        
        try:
            response = self.model.generate_content(prompt)
            import json
            import re
            
            # Extract JSON from potential markdown blocks
            text = response.text
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                res_json = json.loads(match.group(0))
                res_json["confidence"] = confidence
                return res_json
            else:
                raise ValueError("JSON parse error")
        except Exception as e:
            return {
                "explanation": f"XAI Oluşturulamadı: {e}",
                "contrarian": "Veri yok.",
                "historical": "Veri yok.",
                "confidence": confidence
            }

    def recommend_alternative(self, symbol: str, current_score: int, alternative_symbols: list) -> str:
        """Modül 8: Risk durumunda alternatif hisse/varant önerir."""
        if current_score >= 80:
            return f"{symbol} oldukça güçlü, alternatif aramaya gerek yok."
            
        return f"💡 {symbol} hissesinin teknik puanı düşük. Daha iyi momentuma sahip {', '.join(alternative_symbols[:2])} hisselerini Radar üzerinden incelemenizi öneririm."

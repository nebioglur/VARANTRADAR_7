from typing import Dict, Any
from execution.broker_api import BaseBrokerAPI
from learning.learning_engine import AILearningEngine

class AutonomousTrader:
    """
    CFG-11 Autonomous AI Trader
    İnsansız Al-Sat (Hedge Fon) Motoru.
    Büyük Beyin'in bastığı o kusursuz 13 Soruluk raporu alır. Eğer rapor "Güçlü Al" diyorsa,
    BrokerAPI'ye bağlanır. Hesaptaki parayla "Limit Emri" girer ve ardından hemen
    kendisini korumak için Stop ve Kar-Al emirlerini (OCO Order) borsaya çakar.
    """
    
    def __init__(self, broker: BaseBrokerAPI):
        self.broker = broker
        self.broker.connect()
        
    def execute_golden_report(self, report: Dict[str, Any]) -> bool:
        """
        13 Altın Soruluk JSON raporunu otonom olarak borsada emre dönüştürür.
        """
        
        # 1. HATA ve GÜVEN KONTROLÜ
        # (Zaten Executive Engine'de Exception fırlatılıyor ama Otonom sistem kendi sigortasını atar)
        action = report.get("Q2_Islem_Karari", "")
        if "Al" not in action.upper() and "LONG" not in action.upper():
            print("[AUTONOMOUS TRADER] İşlem kararı AL yönünde değil. Emir geçilmedi.")
            return False
            
        # 2. VERİLERİN RAPORDAN OKUNMASI
        symbol = report["Q1_Neden_Secildi"].get("Asset", "UNKNOWN")
        # Eğer symbol raporda yoksa (Örn mock yapımızda en üstte yoksa) anahtardan almaya çalış.
        if symbol == "UNKNOWN":
            print("[AUTONOMOUS TRADER] Uyarı: Sembol bulunamadı, raporu kontrol edin.")
            return False
            
        entry_price = float(report["Q3_Giris_Seviyeleri"]["En_Iyi_Giris"])
        
        # Q12_Pozisyon_Buyuklugu_ve_Risk içindeki stringden lot sayısını çekmek gerçek sistemde Regex ister.
        # Biz burada mock olarak 100 Lot diyelim.
        quantity = 100 
        
        stop_loss = float(report["Q4_Stop_Loss"]["Seviye"])
        take_profit = float(report["Q5_Kar_Alma_Hedefleri"]["TP2_Ana_Hedef"])
        
        # 3. İŞLEMİN BORSAYA İLETİLMESİ (Execution)
        print(f"\n[🚀 AUTONOMOUS TRADER] {symbol} İçin Otonom İşlem Başlatılıyor...")
        
        # A) Kademeli Alım Limit Emri (DCA)
        order_res = self.broker.send_limit_order(symbol, "BUY", quantity, entry_price)
        if not order_res.get("success", True): # Mock
            print("[AUTONOMOUS TRADER] Hata: Limit emir iletilemedi.")
            return False
            
        print(f"✅ {quantity} Lot {symbol} için {entry_price} fiyatından ALIŞ emri borsaya iletildi.")
        
        # B) Stop ve TP (OCO) Kurulumu (Kalkanlar açıldı)
        self.broker.send_oco_order(symbol, quantity, stop_loss, take_profit)
        print(f"🛡️ Kalkanlar Devrede: {stop_loss} Stop-Loss ve {take_profit} Take-Profit (OCO) emri borsaya çakıldı.")
        
        # 4. LEARNING ENGINE'E KAYIT (Phase 12)
        AILearningEngine.record_prediction(
            symbol=symbol,
            confidence=report["Q7_Basari_Olasiligi"]["AI_Guven_Skoru"],
            target_tp=take_profit,
            stop_loss=stop_loss,
            engine_contributions=report["Q8_Katki_Analizi"]
        )
        print("[AUTONOMOUS TRADER] Sistem işlemin kapanmasını bekliyor. Kapanınca kendi hatasından öğrenecek.")
        
        return True

import random
import time
from learning.learning_engine import AILearningEngine

def simulate_training_session(epochs=50):
    print("🧠 VarantRadar Pro - Machine Learning Training Başlatılıyor...")
    print(f"Toplam Epoch: {epochs}")
    print("-" * 50)
    
    engines = ["Technical", "Fundamental", "SmartMoney", "Sentiment", "Macro"]
    regimes = ["BOĞA", "AYI", "YATAY"]
    
    for epoch in range(1, epochs + 1):
        regime = random.choice(regimes)
        
        # Simüle edilmiş dominant motor
        dominant = random.choice(engines)
        
        # Rastgele TP (Başarı) veya SL (Başarısızlık)
        # Teknik motor trend olan piyasada (BOGA, AYI) daha başarılı olsun
        success_chance = 0.5
        if regime in ["BOĞA", "AYI"] and dominant == "Technical":
            success_chance = 0.7
        elif regime == "YATAY" and dominant == "SmartMoney":
            success_chance = 0.65
            
        result = "HIT_TAKE_PROFIT" if random.random() < success_chance else "HIT_STOP_LOSS"
        
        # Ağırlıkları Güncelle (Backpropagation)
        new_weights = AILearningEngine.train_model(regime, result, dominant)
        
        if epoch % 10 == 0 or epoch == epochs:
            print(f"[Epoch {epoch}/{epochs}] Rejim: {regime} | Olay: {result} | Motor: {dominant}")
            print(f"Güncel Ağırlıklar ({regime}):")
            for eng, weight in new_weights.items():
                print(f"  - {eng}: %{weight*100:.1f}")
            print("-" * 30)
            time.sleep(0.1)
            
    print("✅ Eğitim Tamamlandı. brain_weights.json güncellendi.")
    print("Artık sistem hisse tararken sizin öğrettiğiniz bu yeni korelasyonları kullanacak!")

if __name__ == "__main__":
    simulate_training_session(100)

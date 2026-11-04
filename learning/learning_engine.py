import json
import os
from typing import Dict, Any
from datetime import datetime
import pandas as pd

WEIGHTS_FILE = "learning/brain_weights.json"
STATS_FILE = "learning/agent_stats.json"

class AILearningEngine:
    """
    CFG-12 AI Learning Engine (Makine Öğrenimi / Adaptasyon)
    Motor ağırlıklarını (Korelasyon) geçmiş işlemlere göre dinamik olarak günceller.
    Ayrıca her bir yapay zeka ajanının Başarı Oranını (Win-Rate) takip eder.
    """
    
    # Varsayılan (Başlangıç) Ağırlıkları
    DEFAULT_WEIGHTS = {
        "BOGA": {"Technical_AI": 0.35, "SmartMoney_AI": 0.30, "Fundamental_AI": 0.15, "Sentiment_AI": 0.10, "Macro_AI": 0.10},
        "AYI": {"Fundamental_AI": 0.35, "SmartMoney_AI": 0.30, "Technical_AI": 0.15, "Macro_AI": 0.15, "Sentiment_AI": 0.05},
        "YATAY": {"Technical_AI": 0.25, "SmartMoney_AI": 0.25, "Fundamental_AI": 0.25, "Sentiment_AI": 0.15, "Macro_AI": 0.10}
    }

    # No fabricated baseline metrics. Statistics are populated only from recorded outcomes.
    DEFAULT_STATS = {}

    @classmethod
    def load_weights(cls) -> Dict[str, Dict[str, float]]:
        """Ağırlıkları JSON dosyasından okur, yoksa oluşturur."""
        if not os.path.exists(WEIGHTS_FILE):
            cls.save_weights(cls.DEFAULT_WEIGHTS)
            return cls.DEFAULT_WEIGHTS
            
        with open(WEIGHTS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return cls.DEFAULT_WEIGHTS
                
    @classmethod
    def save_weights(cls, weights: Dict[str, Dict[str, float]]):
        """Ağırlıkları JSON dosyasına kaydeder."""
        os.makedirs(os.path.dirname(WEIGHTS_FILE), exist_ok=True)
        with open(WEIGHTS_FILE, "w", encoding="utf-8") as f:
            json.dump(weights, f, indent=4)
            
    @classmethod
    def get_regime_weights(cls, regime: str) -> Dict[str, float]:
        """Piyasa rejimine uygun güncel korelasyon ağırlıklarını döndürür."""
        weights = cls.load_weights()
        if regime in weights:
            return weights[regime]
        return weights["YATAY"]
        
    @classmethod
    def train_model(cls, regime: str, trade_result: str, dominant_engine: str):
        """
        Feedback Loop: İşlem sonucu TP (Take Profit) ise kararı veren motoru ödüllendir, 
        STOP ise cezalandır (Ağırlığı düşür).
        """
        weights = cls.load_weights()
        current_regime_weights = weights.get(regime, cls.DEFAULT_WEIGHTS["YATAY"])
        
        LEARNING_RATE = 0.02 # Her işlemde %2'lik korelasyon değişimi
        
        if trade_result == "HIT_TAKE_PROFIT":
            # Ödül: Dominant motorun ağırlığı artar, diğerleri azalır
            current_regime_weights[dominant_engine] += LEARNING_RATE
        elif trade_result == "HIT_STOP_LOSS":
            # Ceza: Dominant motorun ağırlığı düşer
            current_regime_weights[dominant_engine] -= LEARNING_RATE
            
        # Ağırlıkları normalize et (Toplamı her zaman 1.0 olsun)
        # Negatif ağırlıkları önle
        for eng in current_regime_weights:
            current_regime_weights[eng] = max(0.01, current_regime_weights[eng])
            
        total = sum(current_regime_weights.values())
        for eng in current_regime_weights:
            current_regime_weights[eng] = round(current_regime_weights[eng] / total, 4)
            
        weights[regime] = current_regime_weights
        cls.save_weights(weights)
        
        return current_regime_weights

    @classmethod
    def get_agent_stats(cls) -> Dict[str, Dict[str, Any]]:
        """Ajanların başarı yüzdelerini JSON'dan okur."""
        if not os.path.exists(STATS_FILE):
            cls.save_agent_stats(cls.DEFAULT_STATS)
            return cls.DEFAULT_STATS
            
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return cls.DEFAULT_STATS

    @classmethod
    def save_agent_stats(cls, stats: Dict[str, Dict[str, Any]]):
        """Ajan istatistiklerini JSON'a kaydeder."""
        os.makedirs(os.path.dirname(STATS_FILE), exist_ok=True)
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4)
            
    @classmethod
    def simulate_daily_learning(cls):
        """
        Legacy scheduler compatibility only.
        No synthetic trades, random outcomes, or fabricated win-rate updates are permitted.
        """
        return {
            "status": "DISABLED",
            "reason": "Random learning simulation removed; only verified closed-trade outcomes may update statistics.",
            "stats": cls.get_agent_stats(),
        }

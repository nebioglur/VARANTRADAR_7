import pandas as pd
import numpy as np
import random
from services.backtest_engine import BacktestEngine

class QuantLab:
    """
    VarantRadar Pro V6 - AI Strateji Laboratuvarı (Quant Lab)
    Monte Carlo Simülasyonu, Walk-Forward Analizi ve İşlem Davranışlarını ölçer.
    """
    def __init__(self):
        self.backtest = BacktestEngine()

    def run_monte_carlo(self, backtest_trades: list, iterations: int = 1000) -> dict:
        """
        Modül 4: Monte Carlo Simülasyonu
        Gerçekleşen işlemlerin sırasını rastgele karıştırarak binlerce alternatif evren yaratır.
        Stratejinin tesadüfen mi (Luck factor) kazandırdığını yoksa sağlam mı olduğunu ölçer.
        """
        if not backtest_trades or len(backtest_trades) < 5:
            return {"error": "Monte Carlo için yeterli işlem geçmişi yok (En az 5 işlem gerekli)."}
            
        returns = [t['pnl_pct'] for t in backtest_trades]
        
        final_returns = []
        max_drawdowns = []
        
        for _ in range(iterations):
            # İşlem sırasını rastgele karıştır (Resampling with replacement for robustness)
            simulated_returns = [random.choice(returns) for _ in range(len(returns))]
            
            # Kümülatif Büyüme (100 üzerinden)
            equity = 100.0
            equity_curve = [equity]
            
            for ret in simulated_returns:
                equity *= (1 + (ret / 100))
                equity_curve.append(equity)
                
            final_returns.append(equity)
            
            # Drawdown Hesabı
            eq_series = pd.Series(equity_curve)
            peak = eq_series.cummax()
            drawdown = (eq_series - peak) / peak * 100
            max_drawdowns.append(drawdown.min())

        # İstatistikler
        final_returns = np.array(final_returns)
        max_drawdowns = np.array(max_drawdowns)
        
        # %95 Güven Aralığı
        confidence_interval_low = np.percentile(final_returns, 5)
        confidence_interval_high = np.percentile(final_returns, 95)
        
        # İflas Riski (Ana paranın %50'den fazlasını kaybetme olasılığı)
        ruin_probability = (final_returns < 50.0).sum() / iterations * 100
        
        return {
            "iterations": iterations,
            "median_return": round(np.median(final_returns) - 100, 2), # Yüzde getiri
            "best_case_return": round(np.max(final_returns) - 100, 2),
            "worst_case_return": round(np.min(final_returns) - 100, 2),
            "median_max_drawdown": round(abs(np.median(max_drawdowns)), 2),
            "confidence_interval_low": round(confidence_interval_low - 100, 2),
            "confidence_interval_high": round(confidence_interval_high - 100, 2),
            "ruin_probability_pct": round(ruin_probability, 2)
        }

    def walk_forward_analysis(self, df: pd.DataFrame, strategy_name: str) -> dict:
        """
        Modül 3: Walk-Forward Analysis
        Veriyi %70 Eğitim (In-Sample), %30 Test (Out-of-Sample) olarak böler.
        Eğer test dönemindeki başarı, eğitim dönemine göre çok düşüyorsa strateji "Aşırı Optimize" (Overfitted) edilmiştir.
        """
        if len(df) < 100:
            return {"error": "Walk-Forward için en az 100 bar (gün) veri gerekli."}
            
        split_idx = int(len(df) * 0.70)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        train_results = self.backtest.run_backtest(train_df, strategy_name)
        test_results = self.backtest.run_backtest(test_df, strategy_name)
        
        if "error" in train_results or "error" in test_results:
            return {"error": "Backtest sırasında hata."}
            
        # Dayanıklılık Skoru (Robustness Score): Test Getirisi / Eğitim Getirisi Oranı
        train_return = train_results.get('total_return_pct', 0)
        test_return = test_results.get('total_return_pct', 0)
        
        # Yıllıklandırma (Rough approximation)
        train_days = len(train_df)
        test_days = len(test_df)
        
        train_annualized = (train_return / train_days) * 252 if train_days > 0 else 0
        test_annualized = (test_return / test_days) * 252 if test_days > 0 else 0
        
        if train_annualized <= 0:
            robustness_score = 0
        else:
            robustness_score = min(100, max(0, (test_annualized / train_annualized) * 100))
            
        ai_note = "MÜKEMMEL: Strateji geçmişte de gelecekte de tutarlı çalışıyor." if robustness_score > 70 else \
                  "DİKKAT: Strateji test döneminde performans kaybetti. Aşırı optimizasyon (Overfitting) olabilir." if robustness_score > 40 else \
                  "TEHLİKE: Strateji test döneminde çöktü! Kesinlikle canlı piyasada kullanılmamalı."

        return {
            "train_return_pct": round(train_return, 2),
            "test_return_pct": round(test_return, 2),
            "train_annualized": round(train_annualized, 2),
            "test_annualized": round(test_annualized, 2),
            "robustness_score": round(robustness_score, 2),
            "ai_evaluation": ai_note
        }

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from engines.score_engine import ScoreEngine
from engines.risk_engine import RiskEngine
from engines.asset_engine import StockEngine

def run_test():
    # Mock data
    data = {
        'date': pd.date_range(start='2023-01-01', periods=30),
        'close': [100 + i for i in range(30)],
        'high': [102 + i for i in range(30)],
        'low': [98 + i for i in range(30)],
        'EMA': [95 + i for i in range(30)],
        'MACD': [1.5] * 30,
        'MACD_Signal': [1.0] * 30,
        'RSI': [55] * 30,
        'BB_Upper': [110 + i for i in range(30)],
        'BB_Lower': [90 + i for i in range(30)]
    }
    df = pd.DataFrame(data)
    
    print("Testing ScoreEngine...")
    score_engine = ScoreEngine()
    scores = score_engine.calculate_scores(df)
    print("Scores:", scores)
    
    print("\nTesting RiskEngine...")
    risk_engine = RiskEngine()
    risk = risk_engine.calculate_risk_metrics(df)
    print("Risk Metrics:", risk)
    
    print("\nTesting StockEngine...")
    stock_engine = StockEngine()
    stock_eval = stock_engine.analyze("TEST", df)
    print("Stock Eval:", stock_eval)
    
    print("\nAll engines tested successfully!")

if __name__ == "__main__":
    run_test()

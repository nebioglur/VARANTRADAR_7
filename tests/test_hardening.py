import pandas as pd
import pytest

from engines.backtest_engine import BacktestEngine
from execution.risk_manager import RiskManager
from learning.learning_engine import AILearningEngine
from services.warrant_engine import WarrantEngine
from v8_engine.varrant import VarrantEngine
from v8_engine.breakout import BreakoutEngine


def test_backtest_executes_signal_on_next_bar_not_signal_bar():
    df = pd.DataFrame({"Close": [100.0, 110.0, 121.0]})
    signals = pd.Series([1, 1, 0], index=df.index)
    result = BacktestEngine(initial_capital=1000, commission=0.0).run_backtest(df, signals)
    assert result["position"].tolist() == [0.0, 1.0, 1.0]
    assert result["strategy_returns"].iloc[0] == 0.0


def test_backtest_charges_entry_and_exit_costs():
    df = pd.DataFrame({"Close": [100.0, 100.0, 100.0, 100.0]})
    signals = pd.Series([1, 1, 0, 0], index=df.index)
    result = BacktestEngine(initial_capital=1000, commission=0.001).run_backtest(df, signals)
    assert result["transaction_cost"].tolist() == pytest.approx([0.0, 0.001, 0.0, 0.001])


def test_backtest_rejects_missing_prices_instead_of_filling():
    df = pd.DataFrame({"Close": [100.0, None, 102.0]})
    signals = pd.Series([1, 1, 0], index=df.index)
    with pytest.raises(ValueError):
        BacktestEngine().run_backtest(df, signals)


def test_risk_manager_does_not_force_trade_when_kelly_edge_is_negative():
    result = RiskManager.calculate_position_size(100000, 100, 95, win_rate_pct=30, risk_reward_ratio=2)
    assert result["Recommended_Units"] == 0
    assert result["Max_Risk_Pct"] == 0


def test_risk_manager_caps_risk_at_one_percent():
    result = RiskManager.calculate_position_size(100000, 100, 95, win_rate_pct=80, risk_reward_ratio=3)
    assert result["Max_Risk_Pct"] <= 1.0
    assert result["Actual_Risk_Pct"] <= 1.0


def test_default_warrant_lookup_never_returns_synthetic_contracts():
    engine = WarrantEngine()
    result = engine.generate_warrants_for_stock("THYAO.IS", 300.0)
    assert result.empty


def test_synthetic_warrants_are_explicitly_marked():
    engine = WarrantEngine()
    result = engine.generate_synthetic_warrants_for_stock("THYAO.IS", 300.0)
    assert not result.empty
    assert set(result["instrument_source"]) == {"SYNTHETIC_SIMULATION"}


def test_v8_warrant_lookup_requires_real_provider():
    result = VarrantEngine().find_best_varrant("THYAO.IS", "CALL")
    assert result["status"] == "REAL_CHAIN_UNAVAILABLE"
    assert result["warrant_code"] is None
    assert result["estimated_leverage"] is None


def test_random_learning_simulation_is_disabled_and_does_not_add_trades():
    result = AILearningEngine.simulate_daily_learning()
    assert result["status"] == "DISABLED"
    assert "stats" in result

def test_v8_breakout_exposes_mfi_atr_and_volatility_from_valid_ohlcv():
    close = [100.0 + i * 0.05 for i in range(59)]
    close.append(close[-1] + 2.0)
    df = pd.DataFrame({
        "Open": [value - 0.2 for value in close],
        "High": [value + 0.5 for value in close],
        "Low": [value - 0.5 for value in close],
        "Close": close,
        "Volume": [100000.0] * 59 + [350000.0],
    })
    result = BreakoutEngine().analyze_breakout(df, "TEST")
    assert result["status"] not in {"DATA_INSUFFICIENT", "ERROR"}
    metrics = result["metrics"]
    assert metrics["mfi_14"] is not None
    assert metrics["atr_14"] > 0
    assert metrics["atr_pct"] > 0


def test_v8_breakout_rejects_missing_ohlcv_values():
    df = pd.DataFrame({
        "Open": [100.0] * 30,
        "High": [101.0] * 30,
        "Low": [99.0] * 30,
        "Close": [100.0] * 30,
        "Volume": [None] * 30,
    })
    result = BreakoutEngine().analyze_breakout(df, "TEST")
    assert result["status"] == "DATA_INSUFFICIENT"

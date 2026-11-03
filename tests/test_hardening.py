import pandas as pd
import sqlite3
import pytest

from engines.backtest_engine import BacktestEngine
from execution.risk_manager import RiskManager
from learning.learning_engine import AILearningEngine
from services.warrant_engine import WarrantEngine
from v8_engine.varrant import VarrantEngine
from v8_engine.breakout import BreakoutEngine
from v8_engine.database import V8Database
from v8_engine.regime import MarketRegimeEngine
from services.market_breadth import MarketBreadthEngine
from services.warrant_math import WarrantMath
from services.simulation_engine import SimulationEngine


def test_backtest_executes_signal_on_next_bar_not_signal_bar():
    df = pd.DataFrame({"Close": [100.0, 110.0, 121.0]})
    signals = pd.Series([1, 1, 0], index=df.index)
    result = BacktestEngine(initial_capital=1000, commission=0.0).run_backtest(df, signals)
    assert result["position"].tolist() == [0.0, 1.0, 1.0]
    assert result["return_exposure"].tolist() == [0.0, 0.0, 1.0]
    assert result["strategy_returns"].iloc[0] == 0.0
    assert result["strategy_returns"].iloc[1] == 0.0
    assert result["strategy_returns"].iloc[2] == pytest.approx(0.10)


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

def test_missing_v8_regime_data_is_not_reported_as_neutral_50():
    result = MarketRegimeEngine()._default_regime("DATA_INSUFFICIENT")
    assert result["score"] is None
    assert result["xu100_trend"] is None
    assert result["volatility_state"] is None
    assert result["data_available"] is False


def test_missing_market_breadth_does_not_become_fifty_fifty():
    result = MarketBreadthEngine.get_market_breadth(all_stats={}, xu100_change=float("nan"))
    assert result["regime_code"] == "DATA_INSUFFICIENT"
    assert result["pressure_pct"] is None
    assert result["advance_pct"] is None

def test_black_scholes_zero_volatility_and_expiry_are_finite():
    assert WarrantMath.black_scholes_call(100, 90, 0.5, 0.1, 0.0) >= 0
    assert WarrantMath.black_scholes_put(100, 110, 0.5, 0.1, 0.0) >= 0
    assert WarrantMath.calculate_greeks(100, 100, 0, 0.1, 0.2)["gamma"] == 0


def test_black_scholes_rejects_invalid_market_inputs():
    with pytest.raises(ValueError):
        WarrantMath.black_scholes_call(-100, 100, 1, 0.1, 0.2)

def test_intraday_simulation_risk_budget_is_capped_at_one_percent():
    engine = SimulationEngine(daily_budget=100000)
    allocation, risk_amount = engine._position_allocation(100000, 100, 95, is_bear=False)
    assert risk_amount <= 1000.0
    assert allocation <= 33000.0


def test_intraday_setup_does_not_fabricate_atr_when_bars_are_invalid():
    engine = SimulationEngine()
    bad = pd.DataFrame({
        "Open": [100.0, 101.0, 102.0, 103.0],
        "High": [99.0, 100.0, 101.0, 102.0],
        "Low": [100.0, 101.0, 102.0, 103.0],
        "Close": [100.5, 101.5, 102.5, 103.5],
    })
    assert engine._entry_setup(bad, 104.0) is None

def test_v8_outcome_migration_adds_eod_confirmation_without_dropping_rows():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE v8_outcomes (signal_id TEXT PRIMARY KEY, t_eod_price REAL)")
    cursor.execute("INSERT INTO v8_outcomes (signal_id, t_eod_price) VALUES ('legacy', 101.5)")
    V8Database._migrate_outcomes(cursor, conn)
    row = cursor.execute("SELECT signal_id, t_eod_price, t_eod_confirmed FROM v8_outcomes WHERE signal_id='legacy'").fetchone()
    assert row["signal_id"] == "legacy"
    assert row["t_eod_price"] == 101.5
    assert row["t_eod_confirmed"] == 0

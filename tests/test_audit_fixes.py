import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import numpy as np
import pandas as pd

from data.validation import DataValidator
from engines.backtest_engine import BacktestEngine
from execution.risk_manager import RiskManager
from services.warrant_engine import WarrantEngine
from validation.backtest import BacktestValidator
from v8_engine.breakout import BreakoutEngine
import v8_engine.database as v8_database
from decision.probability import ProbabilityMatrix
from api.auth import is_valid_api_token
from api.main import app as fastapi_app


class AuditFixTests(unittest.TestCase):
    def test_validator_rejects_missing_ohlcv(self):
        frame = pd.DataFrame({"close": np.arange(100, 110, dtype=float)})
        report = DataValidator.validate(frame)
        self.assertFalse(report["is_valid"])

    def test_fastapi_analysis_route_declares_bearer_auth(self):
        operation = fastapi_app.openapi()["paths"]["/api/v1/analyze"]["post"]
        self.assertEqual(operation["security"], [{"HTTPBearer": []}])

    def test_api_token_fails_closed_and_checks_configured_value(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(is_valid_api_token("anything"))
        with patch.dict("os.environ", {"API_AUTH_TOKEN": "test-token"}):
            self.assertTrue(is_valid_api_token("test-token"))
            self.assertFalse(is_valid_api_token("wrong-token"))

    def test_validator_rejects_unsupported_interval(self):
        report = DataValidator.validate(pd.DataFrame(), interval="3m")
        self.assertFalse(report["is_valid"])
        self.assertIn("Desteklenmeyen", report["errors"][0])

    def test_low_volume_does_not_confirm_breakout(self):
        n = 30
        frame = pd.DataFrame({"Open": [100.0] * n, "High": [100.5] * n, "Low": [99.5] * n, "Close": [100.0] * n, "Volume": [1000.0] * n})
        frame.loc[n - 1, ["Open", "High", "Low", "Close", "Volume"]] = [104.0, 106.0, 103.0, 105.0, 300.0]
        result = BreakoutEngine().analyze_breakout(frame, "TEST")
        self.assertFalse(result["is_breakout"])
        self.assertEqual(result["status"], "NO_BREAKOUT")

    def test_warrants_not_fabricated_without_provider(self):
        self.assertTrue(WarrantEngine().generate_warrants_for_stock("THYAO.IS", 300).empty)

    def test_probability_not_invented_without_verified_outcomes(self):
        result = ProbabilityMatrix.calculate_success_probability({"Technical": 95}, "BULL")
        self.assertIsNone(result["Probability_Percent"])
        self.assertEqual(result["Historical_Cases"], 0)

    def test_risk_sizing_caps_at_one_percent_by_default(self):
        result = RiskManager.calculate_position_size(100000, 100, 90, win_rate_pct=95)
        self.assertEqual(result["Max_Risk_Pct"], 1.0)
        self.assertLessEqual(result["Actual_Risk_Pct"], 1.0)

    def test_backtest_ambiguous_stop_target_bar_is_conservative(self):
        frame = pd.DataFrame({"close": [100.0] * 30, "high": [101.0] * 30, "low": [99.0] * 30})
        frame.loc[10, ["high", "low"]] = [111.0, 89.0]
        result = BacktestValidator.run_historical_test("TEST", frame, 100, 90, 110)
        self.assertGreater(result["Ambiguous_Bars_Resolved_As_Stop"], 0)
        self.assertGreaterEqual(result["Resolved_Trades"], result["Ambiguous_Bars_Resolved_As_Stop"] )

    def test_v8_migration_adds_engine_version_and_outcome_columns(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            original = v8_database.DB_PATH
            v8_database.DB_PATH = str(Path(temp_dir) / "v8.sqlite")
            try:
                conn = v8_database.V8Database.get_connection()
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE v8_signals (signal_id TEXT PRIMARY KEY, symbol TEXT, timestamp TEXT, strategy TEXT, market_regime TEXT, score REAL, entry_price REAL, stop_price REAL, target1 REAL, target2 REAL, features_snapshot TEXT, status TEXT)")
                cursor.execute("CREATE TABLE v8_outcomes (signal_id TEXT PRIMARY KEY, final_result TEXT)")
                conn.commit()
                v8_database.V8Database._ensure_columns(cursor, conn, "v8_signals", {"engine_version": "TEXT"})
                v8_database.V8Database._migrate_outcomes(cursor, conn)
                cursor.execute("PRAGMA table_info(v8_signals)")
                signal_columns = {row["name"] for row in cursor.fetchall()}
                cursor.execute("PRAGMA table_info(v8_outcomes)")
                outcome_columns = {row["name"] for row in cursor.fetchall()}
                conn.close()
                self.assertIn("engine_version", signal_columns)
                self.assertIn("t_5m_price", outcome_columns)
                self.assertIn("max_favorable_excursion", outcome_columns)
            finally:
                v8_database.DB_PATH = original

    def test_backtest_cost_is_charged_on_first_entry(self):
        frame = pd.DataFrame({"close": [100.0, 101.0, 102.0]})
        result = BacktestEngine().run_backtest(frame, pd.Series([1, 1, 0]))
        self.assertGreater(result["commission_cost"].iloc[0], 0)


if __name__ == "__main__":
    unittest.main()

# VARANTRADAR_7 hardening audit (2026-11-03)

## Scope and safety boundaries

- Work is isolated on `codex/comprehensive-hardening-2026-11-03`, based on `main`.
- `main` was not modified.
- No merge, deployment, production write, broker order, or external credential rotation was performed.
- Existing SQLite/PostgreSQL tables are migrated additively; legacy trade/equity rows are retained.

## Changes made

### Security
- Removed the embedded PostgreSQL connection string fallback from `services/pg_store.py`.
- Removed `patch_pg_secret.py` from this branch because it reconstructed the same database credential in source code.
- Production now fails closed when `DATABASE_URL` / `SUPABASE_DB_URL` is missing instead of silently starting on an empty local SQLite database.
- Production now fails closed when `SECRET_KEY` is missing; local development gets a process-local random key.
- Restricted CORS to the explicit `CORS_ORIGINS` allow-list (same-origin remains the default).
- Protected system log reads with authenticated admin authorization and removed the dashboard-init authentication bypass.
- Removed token fragments and detailed auth errors from the login log path.
- Restricted Supabase token verification to operator-configured HTTPS issuer URLs. Unverified JWT claims no longer create arbitrary outbound request URLs (SSRF protection).
- Disabled runtime GitHub commit/push behavior. The application must not push runtime cache or user database files to `main`.
- Added ignore rules for local environment files, secrets, runtime data and logs.

### Data quality and market data
- Intraday backtests no longer silently fall back from missing 5-minute OHLCV to a daily candle.
- 5-minute OHLCV rows are checked for finite positive prices, valid high/low relationships and non-negative volume.
- Intraday timestamps are normalized to Europe/Istanbul before session-date filtering.
- Market data rows now carry `interval` and `source` metadata; existing rows are migrated with an explicit legacy default.
- The dip/breakout radar is explicitly identified as a DAILY (6-month) strategy, not a 5-minute scanner.
- Partial current-day daily candles are excluded from the daily dip analysis during the BIST session.
- Dip volume-contraction scoring now tests for actual volume contraction; the prior condition rewarded rising volume under a “volume drying up” label.
- Selling-pressure reduction requires enough recent and prior down-volume observations instead of passing by default when samples are absent.
- Dip OHLCV validation, upper-wick calculation and prior-60-bar resistance reference were corrected.
- V8 XU100 regime analysis requires sufficient valid OHLC data, does not invent a 50% market-breadth value when breadth is missing, exposes breadth availability and labels the timeframe as daily.
- V8 ATR uses Wilder smoothing; breakout analysis now exposes Wilder ATR, MFI(14), ATR percentage and 20-bar realized volatility, and rejects missing/invalid volume instead of assuming neutral values.

### Varants and learning
- Default warrant matching no longer returns generated synthetic contracts.
- Synthetic Black-Scholes examples are available only through an explicitly named simulation method and carry `SYNTHETIC_SIMULATION` provenance.
- V8 warrant selection no longer invents product codes or leverage estimates. Without a verified provider it returns `REAL_CHAIN_UNAVAILABLE`.
- Black-Scholes inputs are validated; zero-volatility and expiry cases are handled explicitly.
- Removed hard-coded agent win-rate baselines and cleared the repository's unverified sample performance figures.
- Disabled the random daily learning routine. Learning statistics must come from recorded, closed outcomes.

### Backtest and risk
- Vectorized backtests now execute a close-observed signal on the next bar, not on the signal bar.
- Entry and exit turnover costs are charged; slippage can be configured in basis points.
- Missing prices/signals and invalid close values are rejected rather than silently filled.
- Intrabar stop/target sequencing is explicitly not modeled by the vectorized engine; use the event-driven simulator for OHLC execution studies.
- Position sizing validates inputs, removes the forced minimum trade when Kelly edge is negative and caps modeled per-trade capital risk at 1%.

### Database migrations
- Replaced destructive legacy `DROP TABLE` migrations for `trades` and `equity_log` with additive owner-column backfills and indexes.
- Added the missing `engine_version` field to trade storage.
- Added a non-destructive V8 signal `engine_version` migration.
- Added interval/source columns to market data storage.

### Tests and CI
- Added `tests/test_hardening.py` regression tests for next-bar backtests, transaction costs, missing data, risk caps, synthetic/real warrant separation, random learning removal, MFI and ATR.
- Added `.github/workflows/tests.yml` to run pytest on Codex/fix branches and pull requests to main.
- CI has not yet been observed passing in this audit report. The tests must be run by GitHub Actions before merge.

## Changed files

- `.gitignore`
- `.github/workflows/tests.yml`
- `server.py`
- `services/pg_store.py`
- `services/trade_database.py`
- `services/market_data.py`
- `services/dip_breakout_engine.py`
- `services/warrant_engine.py`
- `services/warrant_math.py`
- `v8_engine/database.py`
- `v8_engine/regime.py`
- `v8_engine/breakout.py`
- `v8_engine/varrant.py`
- `learning/learning_engine.py`
- `learning/agent_stats.json`
- `execution/risk_manager.py`
- `engines/backtest_engine.py`
- `tests/test_hardening.py`
- Removed `patch_pg_secret.py` from this branch.

## Critical actions still required

1. **Rotate the exposed Supabase/PostgreSQL database password immediately.** The old credential was present in committed source and in a helper script. Removing it from this branch does not erase Git history or the unchanged `main` branch. Revoke the old password, set a new `DATABASE_URL` in the deployment secret store, and arrange a repository-history cleanup after preserving any required backups.
2. The repository currently tracks runtime database/log artifacts (including files under `data/` and `logs/`). New ignore rules do not untrack existing files. Before removing them, export and verify backups; then remove them from repository tracking and clean history.
3. Set `SECRET_KEY`, `DATABASE_URL` (or `SUPABASE_DB_URL`), `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and a narrow `CORS_ORIGINS` list in the deployment environment. Do not commit these values.
4. Existing legacy `equity_log` tables may retain a date-only primary key. The additive migration preserves rows, but that legacy primary-key shape can still prevent multiple owners from storing the same date. A separate verified backup-and-rebuild migration is still required for that legacy schema.
5. Run GitHub Actions and resolve all failures before merge. This environment cannot execute the repository's Python runtime or access the deployment's private database.

## Required external providers / integrations

- **Real BIST warrant chain:** an authorized provider/issuer feed with product code, underlying, CALL/PUT, strike, expiry, multiplier/conversion ratio, bid/ask, last trade, Greeks (or sufficient inputs to calculate them), market status and quote timestamp. No such live provider/API is configured in the inspected repository.
- **Reliable BIST equity/intraday data:** a licensed provider or broker feed with documented 1m/5m OHLCV, exchange timezone, historical retention and corporate-action handling. Yahoo Finance is not a guaranteed real-time exchange feed and must be displayed with its actual source/timestamp.
- **Broker execution:** an explicitly supported brokerage API, credentials, account permissions and preferably a sandbox. The current broker interface is abstract; no live order routing was verified. No real orders are sent by these changes.
- **AI/ML:** a reproducible training dataset of timestamped features and resolved outcomes, plus versioned model artifacts and out-of-sample validation. No random result should be labeled as learned or predictive.

## Not claimed as complete

This is a focused hardening pass, not certification of every module in the 1,921-entry repository tree. The full application still needs an environment-backed end-to-end audit of every API route, UI workflow, scanner, strategy engine, portfolio operation, deployment startup and legacy database migration. No profitability, win-rate, predictive accuracy, live-data latency or broker-execution guarantee is claimed.

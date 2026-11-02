# Security and market data configuration

## Required security actions

A database connection URI was embedded in the repository and has been removed from the current branch. Treat its password as compromised: rotate the Supabase/PostgreSQL database password and update the deployment secret before relying on this branch. Removing it from the latest tree does not remove it from Git history. History rewriting or force-pushing `main` is intentionally outside this change.

Configure `DATABASE_URL` (or `SUPABASE_DB_URL`), `API_AUTH_TOKEN`, and `SECRET_KEY` in the deployment secret store. Configure a stable, high-entropy `SECRET_KEY`; without it sessions reset on restart. If the encrypted API vault is used, configure `API_VAULT_MASTER_KEY` and `API_VAULT_SALT` through a secret manager. Existing vault contents encrypted with the former embedded key cannot be migrated automatically; re-enter provider credentials after rotation. Do not commit `.env`, runtime databases, caches, audit logs, or user-specific output.

Set `CORS_ALLOWED_ORIGINS` to a comma-separated list of exact trusted HTTPS origins for production. The default only permits local development origins. `COOKIE_SECURE` defaults to secure cookies and should remain enabled behind HTTPS.

The former background task that staged runtime data and pushed directly to `main` is disabled. Persist live state in a private database or private object store.

## Market data limitations

No verified BIST warrant instrument-master provider is configured. Static expired symbols and fabricated tradable-looking warrants are therefore disabled. The warrant scanner will remain empty until a licensed/current provider supplies instrument code, underlying, type, strike, ratio, expiry, quote and source timestamp. The theoretical pricing helper is not a market quote.

`YFinanceProvider` is an external fallback, not an exchange-certified feed. Configure `FINNHUB_API_KEY` and/or `TWELVEDATA_API_KEY` only if those services are licensed and configured for the needed BIST symbols and intervals. `IsYatirimProvider` availability and symbol/interval coverage must be verified against provider terms. No provider credentials are supplied by this repository.

No brokerage execution adapter is configured. Portfolio terminal endpoints record simulated/manual position state; they must not be interpreted as broker orders.

## Validation and strategy notes

OHLCV with missing required columns, non-finite prices, invalid price ranges, unsupported intervals, or stale timestamps is rejected. Intraday freshness is capped at 36 hours and daily/longer intervals at 96 hours to allow weekends and holidays; this is a guardrail, not a market-calendar service. Historical backtests conservatively count bars touching both stop and target as stops. Commission is included in the vectorized backtest; spread, slippage, taxes, corporate actions and survivorship bias still require provider-specific modeling.

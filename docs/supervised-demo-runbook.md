# Supervised Demo Lifecycle Runbook

## Purpose

Run one bounded Kalshi demo-market lifecycle session while monitoring logs and
confirming session-owned order cleanup.

This procedure is for the demo environment only. Do not enable real-money
trading.

## Preconditions

- `KALSHI_BOT_ORDER_SUBMISSION_ENABLED=false`
- `KALSHI_BOT_ORDER_CANCELLATION_ENABLED=false`
- A valid demo API key ID and private-key path are configured.
- `KALSHI_BOT_DEMO_MARKET_TICKER` identifies an open demo market.
- `KALSHI_BOT_DEMO_QUOTE_QUANTITY` is positive.
- `KALSHI_BOT_DEMO_MAX_CYCLES` is small, such as `1` or `2`.
- `KALSHI_BOT_DEMO_POLL_INTERVAL_SECONDS` is configured.
- The full test suite, Ruff check, and formatting check pass.

## Dry-Run Session

Keep both order flags disabled.

Run:

```powershell
uv run python -m kalshi_bot.main
```

Confirm the logs contain:

- `application_started`
- `demo_api_data_retrieved`
- `strategy_quotes_decided`
- `quote_risk_evaluated`
- `dry_run_execution_planned`
- `execution_plan_reconciled`
- `demo_api_data_cycle_completed`

Confirm no order is created or cancelled while both flags remain disabled.

## Limited Order-Flow Verification

Only after the dry run is understood:

1. Use the Kalshi demo environment.
2. Choose one open, liquid market.
3. Set `KALSHI_BOT_DEMO_MAX_CYCLES=1`.
4. Use the minimum practical quote quantity.
5. Set both submission and cancellation flags to `true`.
6. Start the lifecycle while watching logs and the Kalshi demo order page.
7. Confirm orders, if submitted, have the current `kbot-...` session prefix.
8. Confirm lifecycle cleanup cancels only orders with that same prefix.

Return both order flags to `false` immediately after the verification.

## Stop Conditions

Stop the session and leave both order flags disabled if any of these occur:

- `demo_api_data_retrieval_failed`
- Repeated `429 Too Many Requests` responses
- Stale market data or a closed market
- An unexpected position or exposure
- An order without the current session prefix
- An order remains resting after expected session cleanup
- A lifecycle and cleanup failure `ExceptionGroup` or `BaseExceptionGroup`

## Post-Run Review

Record:

- Market ticker
- Cycle count
- Session prefix
- Quote and risk decisions
- Planned, submitted, and cancelled order counts
- Inventory action, if any
- Unexpected errors or stop conditions
- Confirmation that no session-owned resting orders remain

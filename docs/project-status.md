# Kalshi Bot Project Status

_Updated: August 8, 2026 — Day 16 complete_

## Executive summary

The project now has a complete, typed path from Kalshi market data to a
flag-gated order-submission boundary, plus an independent command for canceling
all resting orders.

Current application flow:

`Kalshi API -> typed API models -> MarketSnapshot -> QuoteDecision -> RiskDecision -> ExecutionPlan -> flag-gated submission -> structured logs`

Emergency cancellation flow:

`cancel_orders command -> retrieve every resting-order page -> cancel every resting order -> structured completion log`

Day 16 is complete. The latest full local test run passed. Based on the 93 tests
on the currently pushed `main` branch plus the two cancellation-setting tests
and six cancellation-command tests completed locally, the current expected
total is **101 passing tests**.

The bot has not intentionally placed a real order. The current Kalshi demo key
is read-only, order submission defaults to disabled, and order cancellation
defaults to disabled.

## Environment

- Windows and PowerShell
- Cursor
- Python 3.14.6
- uv for Python and dependency management
- pytest for testing
- Ruff for formatting and linting
- Pydantic for typed configuration and API-response validation
- HTTPX for asynchronous HTTP requests
- Cryptography for RSA request signing
- Structlog for structured logging
- GitHub repository: `mjanes7630/kalshi-bot`

## Project structure

```text
kalshi_bot/
  api/
    auth.py
    client.py
    models.py
  execution/
    cancellation.py
    models.py
    planner.py
    submission.py
  marketdata/
    builder.py
    models.py
  models/
    market.py
  risk/
    checks.py
    models.py
  strategy/
    models.py
    quotes.py
  cancel_orders.py
  config.py
  logging_config.py
  main.py

tests/
  test_api_client.py
  test_api_models.py
  test_auth.py
  test_cancel_orders.py
  test_config.py
  test_execution_cancellation.py
  test_execution_planner.py
  test_execution_submission.py
  test_logging_config.py
  test_market.py
  test_marketdata_builder.py
  test_marketdata_models.py
  test_risk_checks.py
  test_strategy_quotes.py
```

## Current implementation

### Configuration and logging

`Settings` loads typed configuration from `.env` and `KALSHI_BOT_`
environment variables.

Current safety-relevant settings include:

- `api_key_id`
- `private_key_path`
- `order_submission_enabled`, defaulting to `False`
- `order_cancellation_enabled`, defaulting to `False`

`.env.example` documents both action flags as disabled. The real `.env` and RSA
private key remain outside version control.

Structlog produces readable development logs and JSON production logs. The
current execution-related events include:

- `dry_run_execution_planned`
- `execution_submission_evaluated`
- `order_cancellation_disabled`
- `order_cancellation_completed`

### Authentication and API client

The bot loads a PEM-formatted RSA private key and signs authenticated Kalshi
requests with RSA-PSS and SHA-256. Query parameters are excluded from the
signed path, matching Kalshi's authentication rules.

`KalshiClient` currently supports:

- Market retrieval
- Market-order-book retrieval
- Recent-trade retrieval
- Balance retrieval
- Position retrieval
- Order creation
- Individual order cancellation
- Paginated resting-order retrieval

The client targets Kalshi's demo REST environment. Tests use mocks or
`httpx.MockTransport`; they do not contact Kalshi.

### Market-data boundary

Pydantic models parse Kalshi's fixed-point strings into `Decimal` values and
timestamps into typed `datetime` values.

`build_market_snapshot()` converts exchange-specific responses into immutable
internal models. It sorts YES bids, converts NO bids into implied YES asks,
sorts asks, filters trades by ticker, and accepts a caller-provided observation
time for deterministic testing.

This keeps strategy code independent of Kalshi JSON field names and response
layout.

### Strategy

`decide_quotes()` is pure and deterministic. It currently:

- Requires both sides of the YES order book
- Joins the best YES bid and best implied YES ask
- Uses an explicit quote quantity
- Produces no quote for incomplete books

The current strategy is intentionally simple. It does not yet account for
fees, inventory, desired edge, volatility, or fill probability.

### Risk

`evaluate_quote_risk()` is pure and deterministic. It currently:

- Rejects incomplete two-sided quotes
- Rejects either side above the configured maximum quote quantity
- Rejects invalid zero or negative limits
- Produces an immutable, observable decision

The current gate does not yet enforce portfolio exposure, available balance,
inventory skew, cumulative loss, market status, or stale-data limits.

### Planning and submission

`create_execution_plan()` converts an approved two-sided quote into immutable
internal `BUY` and `SELL` intents. Rejected risk decisions produce an empty
plan.

`submit_execution_plan()`:

- Returns without API calls when order submission is disabled
- Maps internal sides to Kalshi `bid` and `ask` values
- Generates a unique UUID client order ID for every intent
- Submits orders sequentially
- Tracks only successful submissions
- Cancels successful earlier orders in reverse order if a later submission fails
- Preserves the original submission exception when cleanup succeeds
- Raises an `ExceptionGroup` containing the submission failure and every cleanup
  failure when cleanup also fails

`main.py` now calls this boundary, but the default-disabled setting keeps the
normal application run non-submitting.

### Resting-order cancellation

`retrieve_all_resting_orders()`:

- Retrieves resting orders with the maximum page size
- Follows pagination until the cursor is empty
- Returns an immutable tuple
- Detects a repeated cursor and fails instead of looping forever

`cancel_all_resting_orders()`:

- Returns without API calls when cancellation is disabled
- Attempts every retrieved cancellation even when an earlier one fails
- Returns successful cancellation responses as an immutable tuple
- Raises an `ExceptionGroup` containing all cancellation failures

`kalshi_bot.cancel_orders` is an independent command-line kill switch. Its
orchestration:

1. Loads settings and configures logging.
2. Returns immediately and logs `order_cancellation_disabled` when disabled.
3. Requires the API key ID and private-key path only when enabled.
4. Loads the RSA private key.
5. Opens and safely closes an asynchronous HTTP client.
6. Creates an authenticated `KalshiClient`.
7. Calls the tested resting-order cancellation service.
8. Logs `order_cancellation_completed` with the canceled-order count.

Cancellation cannot undo contracts that filled before the cancellation request
reached Kalshi.

## Safety posture

Implemented safeguards:

- Kalshi demo environment is used.
- The current configured API credential is read-only.
- Submission and global cancellation use separate fail-closed flags.
- Both flags default to `False`.
- The normal application cannot submit unless submission is explicitly enabled.
- The kill-switch command cannot cancel unless cancellation is explicitly enabled.
- Order requests default to post-only and cancel-on-pause behavior.
- Partial two-order submission triggers cleanup of successful earlier orders.
- Cleanup and global cancellation attempt all relevant cancellations.
- Multi-error failures remain observable through `ExceptionGroup`.
- HTTP clients are managed with `async with` and are closed automatically.
- All write-path tests are mocked.

Important remaining limitations:

- A cancellation may arrive after an order has partially or fully filled.
- There is no continuous open-order reconciliation loop.
- There is no inventory, exposure, drawdown, or daily-loss protection.
- There is no stale-market-data or closed-market gate.
- There is no retry, rate-limit, or transient-network policy.
- There is no durable state or restart recovery.
- There is no production deployment or alerting configuration.

## Testing

The expected local suite contains **101 passing test cases**:

| Area | Tests |
|---|---:|
| Market model | 11 |
| Configuration | 8 |
| Logging | 3 |
| API models | 9 |
| API client | 27 |
| Authentication | 3 |
| Market-data models | 4 |
| Snapshot builder | 3 |
| Quote strategy | 4 |
| Quote risk | 7 |
| Execution planner | 5 |
| Execution submission | 6 |
| Resting-order cancellation service | 5 |
| Cancellation command | 6 |
| **Total** | **101** |

The six cancellation-command tests verify:

- Disabled execution returns safely
- Missing API key validation
- Missing private-key-path validation
- Enabled orchestration with mocked dependencies
- Command-line entry-point wiring
- Disabled and successful-completion logging

## Quality gate

Run the complete quality gate with:

```powershell
uv run ruff format .
uv run ruff check .
uv run python -m pytest -v
```

- `uv run` executes each command inside the managed project environment.
- `ruff format .` formats applicable files under the current directory.
- `ruff check .` checks the same project for lint and code-quality problems.
- `python -m pytest -v` runs the complete test suite and prints every test name.
- Each `.` means the current directory.
- PowerShell runs the three lines sequentially.

Expected results:

- Ruff formatting completes successfully.
- Ruff reports `All checks passed!`.
- pytest reports all tests passing; the expected current total is `101 passed`.

## Completed checkpoints

| Day | Result | Test milestone |
|---:|---|---:|
| 1 | Project, package, uv, pytest, Ruff, Cursor, and GitHub setup | — |
| 2 | Decimal-ready market model, calculations, validation, and unit tests | — |
| 3 | Typed settings, `.env`, structured logging, and logging tests | 16 |
| 4 | `Decimal` prices, typed market responses, and asynchronous API client | 21 |
| 5 | RSA authentication, typed balance response, and live read-only verification | 26 |
| 6 | Order book, trades, positions, validation, and read-only API integration | 43 |
| 7 | Immutable market snapshot and exchange-to-domain builder | 50 |
| 8 | Pure two-sided quote strategy | 54 |
| 9 | Pure quote risk gate | 61 |
| 10 | Immutable order intents and dry-run execution planner | 66 |
| 11 | Typed V2 create-order API boundary and disabled submission flag | 73 |
| 12 | Execution-plan mapping and flag-gated submission orchestration | 77 |
| 13 | Typed cancellation API and partial-submission cleanup | 82 |
| 14 | Multi-failure cleanup observability with `ExceptionGroup` | 83 |
| 15 | Connected submission to `main.py` behind the disabled flag and added submission-result logging | 83 |
| 16 | Resting-order pagination, cancel-all service, independent kill-switch command, and cancellation logging | 101 |

## Remaining development

### Milestone 1: first deliberately operational demo bot

Estimated remaining work: **2–3 focused development days**.

1. Add an explicit, tightly limited demo-order verification command using a
   separate full-access demo credential.
2. Submit the smallest permitted post-only demo order, verify the response,
   retrieve the resting order, and cancel it immediately.
3. Add a bounded single-market quote lifecycle: retrieve, decide, risk-check,
   reconcile, submit or replace, and cancel during graceful shutdown.
4. Keep maximum cycles, polling interval, quantity, ticker, and both action
   flags explicit and fail-closed.

At this milestone the bot can operate on one demo market for a bounded period.
It should not yet be treated as safe for unattended real-money operation.

### Milestone 2: reliable unattended demo operation

Estimated additional work: **5–8 development days** after Milestone 1.

- Reconcile desired quotes against actual resting orders instead of blindly
  submitting new orders.
- Add balance, inventory, per-market exposure, portfolio exposure, and loss
  limits.
- Add market-status, stale-data, spread, and fee/profitability gates.
- Add timeout, retry, exponential-backoff, and rate-limit handling.
- Add graceful shutdown and startup recovery drills.
- Add structured cycle summaries, error alerts, and fault-injection tests.
- Run extended demo soak tests and review behavior after partial fills.

### Milestone 3: small live-money pilot

Estimated additional work: **5–10 development days**, plus a deliberate demo
soak period, after Milestone 2.

- Add durable order and fill reconciliation across restarts.
- Add hard daily-loss and total-exposure circuit breakers.
- Add deployment, monitoring, alerts, and operational runbooks.
- Test credential rotation and kill-switch operation from the deployed
  environment.
- Start with one market, minimum size, short sessions, and supervised operation.

## Overall progress estimate

- **About 80–85% complete** toward a bounded, operational single-market demo bot.
- **About 55–65% complete** toward a reliable unattended demo bot.
- **About 40–50% complete** toward a responsibly supervised live-money pilot.

The foundational architecture is largely complete: typed data, authentication,
strategy, risk, planning, submission, cleanup, cancellation, logging, and tests
all have explicit boundaries. Most remaining work is no longer basic Python
plumbing; it is order-lifecycle management, broader risk control, recovery,
observability, and operational validation.

## Next checkpoint

Day 17 should prepare the controlled demo-order verification path without
changing either action flag's safe default. No full-access credential should be
added to the repository, and no order should be submitted until the exact
ticker, size, price behavior, cancellation sequence, and operator checkpoint
have been reviewed.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue using incremental TDD checkpoints.
- The user manually types project code.
- Bundle routine formatting, linting, and full-suite commands when practical.
- Do not advance a write-capable checkpoint until the preceding safety and test
  foundation passes.

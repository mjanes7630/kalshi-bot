# Kalshi Bot Project Status

_Updated: August 17, 2026 — Day 22 complete_

## Executive summary

The bot now has a typed, tested path from Kalshi demo-market data through quote strategy, risk checks, execution planning, reconciliation, inventory safety, and bounded single-market lifecycle cleanup.

`Kalshi API -> typed API models -> MarketSnapshot -> QuoteDecision -> position + balance risk gates -> ExecutionPlan -> session-scoped reconciliation -> safe inventory flattening -> flag-gated execution -> bounded polling -> session cleanup -> structured logs`

Day 22 adds bounded resilience for read-only API requests. GET requests retry transient transport failures and rate-limit responses without making order-writing behavior less safe.

The complete local suite passes with **224 tests**. Ruff linting and formatting pass. Order submission and cancellation remain disabled by default in the private `.env`.

## Environment

- Windows and PowerShell
- Cursor
- Python 3.14.6 managed with uv
- pytest and Ruff
- Pydantic, HTTPX, Cryptography, and Structlog
- GitHub repository: `mjanes7630/kalshi-bot`

## Project structure

```text
kalshi_bot/
  api/                 # Authentication, typed HTTP client, API models
  execution/           # Plans, submission, cancellation, reconciliation
  marketdata/          # Exchange-to-domain snapshot boundary
  models/              # Internal market model
  risk/                # Pure risk decisions and checks
  strategy/            # Pure quote decisions
  cancel_orders.py
  config.py
  demo_order.py
  logging_config.py
  main.py

tests/                 # Unit and lifecycle integration tests
```

## Current implementation

### Configuration and logging

`Settings` loads typed configuration from `.env` and `KALSHI_BOT_` environment variables. Separate submission and cancellation flags both default to `False`. The lifecycle uses one configured market, a positive quote quantity, a bounded cycle count, and a polling interval.

Risk settings include a maximum market-data age, projected per-market-exposure cap, projected available-balance floor, and inventory-flattening controls. Credentials and private keys remain outside version control.

### API client and market-data boundary

The client uses RSA-PSS/SHA-256 to sign authenticated Kalshi demo requests. It supports market lookup, order books, trades, balance, positions, single-order and paginated resting-order reads, event-order creation, and cancellation.

Typed Pydantic models convert fixed-point API values to `Decimal`; `build_market_snapshot()` creates the immutable domain snapshot consumed by the strategy and risk layers.

#### Read-only retry policy

All GET methods use one bounded retry helper:

- Up to three total attempts: the original request and two retries.
- Retries `httpx.TransportError` failures such as connection loss and timeouts.
- Retries `HTTPStatus.TOO_MANY_REQUESTS` (`429`) responses.
- Uses exponential fallback waits of 0.1 then 0.2 seconds.
- Honors a valid non-negative numeric `Retry-After` header on a `429`.
- Safely falls back when that header is missing, malformed, or negative.
- Leaves all other HTTP responses to the calling method's `response.raise_for_status()` handling.

Order-creation and cancellation methods deliberately do **not** use this helper. A timed-out POST or DELETE may have been processed by Kalshi; resending it could create an ambiguous or duplicate action. Tests explicitly prove these write requests are attempted once only.

### Strategy, risk, and inventory safety

`decide_quotes()` is pure and deterministic. It requires a complete two-sided YES book and produces a bid and ask at the configured quantity; incomplete books produce no quote.

`evaluate_quote_risk()` requires an open, fresh market and checks projected per-market exposure and available balance before an execution plan can contain new quotes. Quote reservation conservatively assumes both proposed sides can expose the account at once.

Day 21 adds inventory flattening safeguards. When reconciliation identifies open YES inventory that should be removed, it cancels the relevant resting quote before submitting the flattening intent. Long YES inventory is flattened by selling YES; short YES inventory is flattened by buying YES. This prevents a resting quote from increasing the directional position while the bot is trying to remove it.

### Planning, execution, cancellation, and reconciliation

`create_execution_plan()` maps approved quotes to immutable intents. `submit_execution_plan()` is disabled unless explicitly enabled, uses unique client order IDs, and cleans up earlier successful submissions in reverse order if a later submission fails. Multiple failures remain visible through `ExceptionGroup`.

Resting-order retrieval is paginated and rejects repeated cursors. Reconciliation considers only session-owned client order IDs, cancels unwanted orders, preserves matching desired orders, submits missing intents, and does not replace a quote when prerequisite cancellation fails or is disabled.

The independent `cancel_orders` command remains a separately gated kill switch. It cannot reverse an order that has already filled.

### Bounded lifecycle and controlled demo order

`run_demo_lifecycle()` runs the configured market for a bounded cycle count and waits only between cycles. Every run has one shared `kbot-...` session prefix. `retrieve_demo_api_data()` obtains market data, positions, and balance before risk evaluation and reconciliation.

A `finally` block performs session-scoped cleanup after normal completion or a lifecycle error when cancellation is enabled. `kalshi_bot.demo_order` remains a separate, intentionally limited create-and-immediately-cancel verification command.

## Safety posture

Implemented safeguards:

- Demo environment only; write paths are disabled by default.
- Open-market, fresh-observation, exposure, and available-balance gates.
- Conservative two-sided quote reservation.
- Post-only and cancel-on-pause order behavior.
- Inventory flattening cancels conflicting resting quotes first.
- Session-scoped reconciliation and cleanup.
- Independently gated global cancellation.
- Reverse-order cleanup after partial submission failure.
- Aggregated cancellation failures through `ExceptionGroup`.
- Bounded retries only for idempotent read requests.
- Explicit no-retry protection for order creation and cancellation.
- Typed, mocked tests around all write-capable behavior.

Important remaining limitations:

- A cancellation or flattening order can still arrive after a partial or full fill.
- There is no durable restart recovery or persisted fill/order state.
- There are no portfolio-wide exposure, drawdown, or daily-loss circuit breakers.
- There is no alerting, deployment, or completed sustained demo soak test.
- Only `429` response-rate limiting is retried; other HTTP error responses are intentionally surfaced immediately for now.

## Testing and quality gate

The latest full suite passed with **224 tests**.

Coverage includes typed API models and request boundaries, configuration validation, market-data building, quote decisions, risk gates, inventory flattening, pagination, cancellation, partial-submission cleanup, reconciliation, bounded lifecycle behavior, session cleanup, and the controlled demo-order flow.

Day 22 additionally covers:

- transport recovery, exponential backoff, and retry exhaustion;
- `429` retry and exhaustion;
- valid, malformed, and negative `Retry-After` handling;
- every supported GET method using the retry helper;
- exactly-one-attempt behavior for create and cancel writes.

Final validation:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest
```

Expected result: Ruff formatting and lint checks complete successfully, and pytest reports `224 passed`.

## Completed checkpoints

| Day | Result | Test milestone |
|---:|---|---:|
| 1 | Project, package, uv, pytest, Ruff, Cursor, and GitHub setup | — |
| 2 | Decimal-ready market model, calculations, validation, and unit tests | — |
| 3 | Typed settings, `.env`, structured logging, and logging tests | 16 |
| 4 | Decimal prices, typed market responses, and asynchronous API client | 21 |
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
| 15 | Connected submission to `main.py` behind disabled submission | 83 |
| 16 | Resting-order pagination, independent kill switch, and cancellation logging | 101 |
| 17 | Isolated demo command, corrected event-order IDs, and live verification | 124 |
| 18 | Resting-order reconciliation and `main.py` lifecycle integration | 148 |
| 19 | Bounded lifecycle, session ownership, and shutdown cleanup | 165 |
| 20 | Fresh-data, projected-exposure, and projected-balance safeguards | 184 |
| 21 | Inventory flattening and pre-flatten quote-cancellation safety | 206 |
| 22 | Read-only retry, backoff, rate-limit handling, and write no-retry guarantees | 224 |

## Remaining development

### Milestone 1: reliable bounded demo lifecycle

Estimated remaining work: **one focused development day**, followed by a deliberately bounded supervised demo exercise.

**Day 23 — operational visibility and fault-injection coverage**

1. Structured per-cycle outcome summaries: market-data result, risk reason, reconciliation actions, submission outcome, and inventory state.
2. Clear structured error logging for exhausted read retries and failed reconciliation actions, without leaking credentials or request bodies.
3. Lifecycle-level fault-injection tests: a transient GET failure is recoverable; an exhausted failure is observable and leaves client/session cleanup in a safe state.
4. A concise runbook for a bounded, supervised demo-lifecycle exercise.

This is a moderate workload: roughly **8–12 focused tests**, several structured-log events, and no new order type or expanded live-trading authority.

### Milestone 2: reliable unattended demo operation

Estimated additional work: **4–7 development days** after Milestone 1.

- Startup recovery and reconciliation drills.
- Durable order and fill tracking across restarts.
- Portfolio-wide exposure and daily-loss circuit breakers.
- Extended demo soak testing, alerts, and operational runbooks.

### Milestone 3: small live-money pilot

Estimated additional work: **5–10 development days**, plus a deliberate demo soak period, after Milestone 2.

- Deployment, monitoring, and credential-rotation procedures.
- Deployed kill-switch verification.
- One market, minimum size, short supervised sessions.

## Overall progress estimate

- **96–98% complete** toward a bounded, supervised single-market demo.
- **74–82% complete** toward a reliable unattended demo bot.
- **58–68% complete** toward a responsibly supervised live-money pilot.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue with incremental TDD checkpoints and identify each test type.
- The user manually types project code.
- Do not advance a write-capable checkpoint until the preceding safety and test foundation passes.


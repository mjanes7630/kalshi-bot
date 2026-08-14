# Kalshi Bot Project Status

_Updated: August 14, 2026 — Day 20 complete_

## Executive summary

The bot now has a complete, typed path from Kalshi market data to a bounded,
configured single-market demo lifecycle. Before reconciliation can submit an
order, the lifecycle retrieves the current position and available balance and
applies risk gates to the proposed two-sided quote.

`Kalshi API -> configured market -> typed API models -> MarketSnapshot -> QuoteDecision -> positions and balance -> RiskDecision -> ExecutionPlan -> session-scoped reconciliation -> flag-gated submission -> bounded polling -> session-scoped cleanup -> structured logs`

Day 20 is complete. Ruff formatting and linting passed, and the complete local
test suite passed with **184 tests**.

The normal bot cannot submit or cancel unless its separate safety flags are
explicitly enabled. Both flags remain `false` in the private `.env` outside
controlled testing.

## Environment

- Windows and PowerShell
- Cursor
- Python 3.14.6 with uv
- pytest and Ruff
- Pydantic, HTTPX, Cryptography, and Structlog
- GitHub repository: `mjanes7630/kalshi-bot`

## Project structure

```text
kalshi_bot/
  api/                 # Authentication, HTTP client, typed API models
  execution/           # Planning, submission, cancellation, reconciliation
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

`Settings` loads typed configuration from `.env` and `KALSHI_BOT_`
environment variables. Safety-relevant settings include:

- Separate `order_submission_enabled` and `order_cancellation_enabled` flags,
  both defaulting to `False`.
- Required lifecycle ticker and strictly positive quote quantity.
- Bounded lifecycle count and polling interval.
- Maximum observation age, defaulting to 30 seconds.
- Maximum projected per-market exposure, defaulting to $5.00.
- Minimum projected available balance, defaulting to $10.00.
- Tightly limited demo-order ticker, count, and price settings.

`.env.example` documents these controls without enabling either action flag.
The full-access demo credential, private `.env`, and RSA key remain outside
version control.

### API client and market-data boundary

The client signs authenticated Kalshi demo-environment requests with RSA-PSS
and SHA-256. It supports configured market lookup, order books, recent trades,
balance, positions, individual and paginated resting-order reads, event-order
creation, and individual event-order cancellation.

Typed Pydantic API models parse fixed-point values into `Decimal` and times
into `datetime`. `build_market_snapshot()` converts exchange models into
immutable internal data: it sorts YES bids, converts NO bids to implied YES
asks, filters trades for the market, and accepts a provided observation time for
deterministic tests.

### Strategy and risk gates

`decide_quotes()` is pure and deterministic. It requires a complete two-sided
YES book and produces a bid and ask at the configured quantity; incomplete
books produce no quote.

`evaluate_quote_risk()` is pure and deterministic. An execution plan can
contain orders only when the quote is complete and within its quantity limit,
the market is `open`, the observation is fresh, and the projected limits pass:

- Current market exposure plus the proposed quote reservation is no more than
  the configured exposure cap.
- Available balance minus the proposed quote reservation is at least the
  configured balance floor.

The quote reservation deliberately assumes both proposed sides can expose the
account at once:

- YES bid: `price × quantity`.
- YES ask: `(1.00 - price) × quantity`.

For a two-contract bid at $0.42 and ask at $0.44, the reservation is
$0.84 + $1.12 = $1.96. This avoids assuming both orders will fill and offset
immediately. It is intentionally conservative and may reject some
inventory-offset situations that are actually safe.

### Planning, submission, cancellation, and reconciliation

`create_execution_plan()` maps approved two-sided quotes into immutable
`BUY` and `SELL` intents. Rejected risk decisions create empty plans.

`submit_execution_plan()` does nothing when submission is disabled. When
enabled, it creates unique client order IDs, submits sequentially, and cancels
earlier successful submissions in reverse order if a later submission fails.
Combined submission and cleanup failures remain visible in an `ExceptionGroup`.

Resting-order retrieval follows pagination and rejects repeated cursors.
Cancellation safely returns when disabled, attempts every requested
cancellation, and aggregates failures. Reconciliation considers only the
active bot session's order IDs, cancels unwanted session-owned orders, and
submits only missing desired intents.

The independent `cancel_orders` command is a kill switch for resting orders.
It cannot reverse an order that filled before the cancellation arrived.

### Bounded single-market lifecycle

`run_demo_lifecycle()` defaults to one cycle, runs only the configured market,
and waits only between cycles. Every run has one `kbot-...` session prefix
reused for that run's client order IDs.

During each cycle, `retrieve_demo_api_data()` retrieves market data,
positions, and balance. It finds the configured market's current exposure and
passes it with the available balance to risk evaluation before reconciliation.
These account values can therefore prevent new orders rather than simply being
logged afterward.

A Python `finally` block—the equivalent of C# `finally`—performs
session-scoped cleanup after normal completion or a lifecycle error, provided
cancellation is explicitly enabled.

### Controlled demo-order verification

`kalshi_bot.demo_order` is separate from the normal lifecycle. It requires
both action flags, creates one minimum post-only demo order, logs the local and
exchange order IDs, immediately cancels the exchange order ID, and closes the
HTTP client.

The successful Day 17 manual demo result was:

```text
POST /portfolio/events/orders                 -> 201 Created
DELETE /portfolio/events/orders/{order_id}    -> 200 OK
demo_order_command_completed                  -> logged
```

## Safety posture

Implemented safeguards:

- Demo environment only; write paths remain disabled by default.
- Configured ticker, positive quantity, bounded cycles, and session isolation.
- Open-market and fresh-observation gates before orders are planned.
- $5.00 projected per-market exposure cap.
- $10.00 projected available-balance floor.
- Conservative reservation of both sides of a proposed quote.
- Post-only and cancel-on-pause order behavior.
- Session-scoped cleanup and independently gated global cancellation.
- Reverse-order cleanup after partial submission failure.
- Aggregated cancellation failures using `ExceptionGroup`.
- Typed, mocked tests around all write-capable paths.

Important remaining limitations:

- Cancellation can arrive after an order partially or fully fills.
- The bot does not yet explicitly flatten inventory before market close. A
  filled sell with no offsetting YES inventory can remain short YES and settle
  directionally if it cannot be bought back while the market is open.
- Reservation does not yet offset a sell against confirmed owned YES inventory.
- No portfolio-wide exposure, drawdown, or daily-loss circuit breakers yet.
- No timeout/retry/backoff/rate-limit policy, durable restart recovery,
  deployment, alerting, or completed demo soak test.

## Testing and quality gate

The latest complete local suite passed with **184 tests**.

Coverage includes typed API/client boundaries, configuration validation,
market-data building, quoting, risk decisions, projected exposure and balance
boundaries, paging, cancellation, partial-submission cleanup, reconciliation,
bounded lifecycle behavior, session cleanup, and controlled demo-order creation
and cancellation.

The final Day 20 quality gate passed:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest
```

Expected result: Ruff formatting and lint checks complete successfully, and
pytest reports `184 passed`.

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
| 19 | Bounded configured lifecycle, session ownership, and shutdown cleanup | 165 |
| 20 | Fresh-market, projected-exposure, and projected-balance safeguards | 184 |

## Remaining development

### Milestone 1: reliable bounded demo lifecycle

Estimated remaining work: **1–3 focused development days**, followed by a
deliberately bounded supervised demo exercise.

1. Add explicit inventory handling and flatten long or short YES positions
   before a market closes.
2. Add timeout, retry, exponential-backoff, and rate-limit handling.
3. Add cycle summaries, fault-injection tests, error alerts, and a bounded live
   demo exercise.

### Milestone 2: reliable unattended demo operation

Estimated additional work: **4–7 development days** after Milestone 1.

- Startup recovery and reconciliation drills.
- Durable order and fill tracking across restarts.
- Portfolio-wide exposure and daily-loss circuit breakers.
- Extended demo soak testing, alerts, and operational runbooks.

### Milestone 3: small live-money pilot

Estimated additional work: **5–10 development days**, plus a deliberate demo
soak period, after Milestone 2.

- Deployment, monitoring, and credential-rotation procedures.
- Deployed kill-switch verification.
- One market, minimum size, short supervised sessions.

## Overall progress estimate

- **About 92–96% complete** toward a bounded, supervised single-market demo.
- **About 70–78% complete** toward a reliable unattended demo bot.
- **About 55–65% complete** toward a responsibly supervised live-money pilot.

## Next checkpoint

Day 21 should focus on inventory safety: identify filled one-sided positions,
cancel remaining resting orders when appropriate, and flatten long or short YES
inventory while the market is still tradable. Both action flags remain disabled
by default.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue using incremental TDD checkpoints.
- The user manually types project code.
- Bundle routine formatting, linting, and full-suite commands when practical.
- Do not advance a write-capable checkpoint until the preceding safety and test
  foundation passes.


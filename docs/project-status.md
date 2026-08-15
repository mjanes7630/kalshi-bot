# Kalshi Bot Project Status

_Updated: August 14, 2026 — Day 21 complete_

## Executive summary

The bot now has a complete, typed path from Kalshi market data to a bounded,
configured single-market demo lifecycle. It can identify confirmed YES
inventory, stop quoting, and attempt to return that inventory to zero while the
market is still open and the market observation is fresh.

`Kalshi API -> configured market -> typed API models -> MarketSnapshot -> QuoteDecision -> positions and balance -> RiskDecision -> ExecutionPlan or inventory-flattening plan -> session-scoped reconciliation -> flag-gated submission -> bounded polling -> session-scoped cleanup -> structured logs`

Day 21 is complete. Ruff formatting and linting passed, and the complete local
test suite passed with **206 tests**.

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
environment variables. Safety-relevant settings include separate submission and
cancellation flags, a configured ticker, positive quote quantity, bounded
lifecycle count and polling interval, a 30-second maximum observation age, a
$5.00 projected per-market exposure cap, and a $10.00 projected available
balance floor.

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

### Strategy and quote risk gates

`decide_quotes()` is pure and deterministic. It requires a complete two-sided
YES book and produces a bid and ask at the configured quantity; incomplete
books produce no quote.

`evaluate_quote_risk()` is pure and deterministic. Normal quote plans require
a complete, size-bounded quote, an open market, fresh data, projected exposure
within the configured cap, and projected available balance at or above the
configured floor. Quote reservation conservatively assumes both proposed sides
could expose the account at once.

### Inventory safety and flattening

`decide_inventory_action()` is a pure inventory decision:

- Positive YES position: sell the owned YES quantity to flatten back to zero.
- Negative YES position: buy the owed YES quantity to flatten back to zero.
- Zero position: take no inventory action.

It accepts only finite `Decimal` positions. `can_flatten_inventory()` reuses
the existing open-market and freshness rules. The lifecycle can therefore
attempt a flatten only from fresh data while the market is still tradable.

`create_flattening_order_intent()` is also pure. It sells long YES inventory at
the best YES bid or buys short YES inventory at the best YES ask. It rejects a
ticker/snapshot mismatch, a closed market, a non-positive quantity, or an
absent matching price level.

Flattening intents are deliberately different from normal market-making quotes:

- `post_only=False` permits taking available liquidity.
- `IMMEDIATE_OR_CANCEL` fills immediately up to the requested quantity and
  cancels any unfilled remainder instead of leaving a new resting order.

The execution model carries these settings explicitly. Existing quote intents
retain the safe defaults: post-only and good-till-canceled.

### Planning, submission, cancellation, and reconciliation

`create_execution_plan()` maps approved two-sided quotes into immutable BUY and
SELL intents. Rejected quote-risk decisions create empty plans.

When non-zero inventory is present and the inventory guard approves, the
lifecycle replaces the normal quote plan with a single flattening intent.
Reconciliation sees an IOC/non-post-only flattening intent as distinct from any
resting quote, even if its market, side, price, and quantity coincide. It first
cancels session-owned resting orders and only then submits the flattening order
when both actions are enabled.

`submit_execution_plan()` does nothing when submission is disabled. When
enabled, it creates unique client order IDs, submits sequentially, and cancels
earlier successful submissions in reverse order if a later submission fails.
Combined submission and cleanup failures remain visible in an `ExceptionGroup`.

### Bounded single-market lifecycle

`run_demo_lifecycle()` defaults to one cycle, runs only the configured market,
and waits only between cycles. Every run has one `kbot-...` session prefix
reused for that run's client order IDs.

During each cycle, `retrieve_demo_api_data()` retrieves market data, positions,
and balance. Confirmed position and balance values feed the relevant decision
layers before reconciliation. The lifecycle uses one timestamp for the quote
risk and inventory-freshness checks in a cycle.

A Python `finally` block—the equivalent of C# `finally`—performs session-scoped
cleanup after normal completion or a lifecycle error, provided cancellation is
explicitly enabled.

### Controlled demo-order verification

`kalshi_bot.demo_order` remains separate from the normal lifecycle. It requires
both action flags, creates one minimum post-only demo order, logs the local and
exchange order IDs, immediately cancels the exchange order ID, and closes the
HTTP client.

## Safety posture

Implemented safeguards:

- Demo environment only; write paths remain disabled by default.
- Configured ticker, positive quantity, bounded cycles, and session isolation.
- Open-market and fresh-observation gates before normal quotes and inventory
  flattening are planned.
- $5.00 projected per-market exposure cap and $10.00 balance floor for normal
  quotes.
- Conservative reservation of both sides of a proposed quote.
- Post-only and cancel-on-pause normal quote behavior.
- Non-post-only immediate-or-cancel flattening behavior.
- Session-scoped cleanup, independently gated cancellation, and reverse-order
  cleanup after partial submission failure.
- Aggregated cleanup failures using `ExceptionGroup`.
- Typed, mocked tests around all write-capable paths.

Important remaining limitations:

- An IOC flattening attempt can partially fill. The next bounded cycle may
  attempt to flatten the remaining position while the market is still open.
- If a market is closed, paused, stale, or lacks matching liquidity, the bot
  cannot safely create a flattening intent.
- No timeout/retry/backoff/rate-limit policy, durable restart recovery,
  portfolio-wide exposure limit, drawdown circuit breaker, alerting, or
  completed supervised demo soak test yet.

## Testing and quality gate

The latest complete local suite passed with **206 tests**.

Day 21 coverage includes long, short, zero, invalid, and non-finite inventory
positions; best-bid/best-ask flattening prices; closed, stale, mismatched, and
unpriceable safety cases; non-post-only IOC request mapping; reconciliation of
resting quotes versus flattening intents; cancellation-before-flattening
ordering; and lifecycle selection of a flattening plan.

The Day 21 quality gate passed:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest
```

Expected result: Ruff formatting and lint checks complete successfully, and
pytest reports `206 passed`.

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
| 21 | Inventory detection, IOC flattening, and cancel-before-flatten ordering | 206 |

## Remaining development

### Milestone 1: reliable bounded demo lifecycle

Estimated remaining work: **1–2 focused development days**, followed by a
deliberately bounded supervised demo exercise.

1. Add timeout, retry, exponential-backoff, and rate-limit handling.
2. Add cycle summaries, fault-injection tests, error alerts, and a bounded live
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

- **About 94–97% complete** toward a bounded, supervised single-market demo.
- **About 72–80% complete** toward a reliable unattended demo bot.
- **About 58–68% complete** toward a responsibly supervised live-money pilot.

## Next checkpoint

Day 22 should focus on resilient API operations: bounded timeouts, retry and
exponential-backoff policy, rate-limit handling, and tests that prove failures
remain visible without creating duplicate orders.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue using incremental TDD checkpoints.
- The user manually types project code.
- Bundle routine formatting, linting, and full-suite commands when practical.
- Do not advance a write-capable checkpoint until the preceding safety and test
  foundation passes.


# Kalshi Bot Project Status

_Updated: August 13, 2026 — Day 19 complete_

## Executive summary

The project now has a complete, typed path from Kalshi market data to a bounded,
configured single-market demo lifecycle. The lifecycle reconciles desired quotes
against resting orders, submits and cancels only behind explicit flags, and
performs session-scoped cleanup when it ends or fails.

Current application flow:

`Kalshi API -> configured market -> typed API models -> MarketSnapshot -> QuoteDecision -> RiskDecision -> ExecutionPlan -> session-scoped reconciliation -> flag-gated submission -> bounded polling -> session-scoped cleanup -> structured logs`

Emergency cancellation flow:

`cancel_orders command -> retrieve every resting-order page -> cancel every resting order -> structured completion log`

Controlled demo-order flow:

`demo_order command -> create one minimum post-only demo order -> log exchange order ID -> cancel immediately -> completion log`

Day 19 is complete. Ruff lint and formatting checks passed, and the full local
suite passed with **165 tests**.

The normal bot remains unable to submit or cancel unless its separate safety
flags are explicitly enabled. Both flags remain `false` in the private `.env`
outside controlled testing.

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
    lifecycle.py
    models.py
    planner.py
    reconciliation.py
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
  demo_order.py
  logging_config.py
  main.py

tests/
  test_api_client.py
  test_api_models.py
  test_auth.py
  test_cancel_orders.py
  test_config.py
  test_demo_order.py
  test_execution_cancellation.py
  test_execution_lifecycle.py
  test_execution_planner.py
  test_execution_reconciliation.py
  test_execution_submission.py
  test_logging_config.py
  test_main_errors.py
  test_main_lifecycle.py
  test_market.py
  test_marketdata_builder.py
  test_marketdata_models.py
  test_risk_checks.py
  test_strategy_quotes.py
```

## Current implementation

### Configuration and logging

`Settings` loads typed configuration from `.env` and `KALSHI_BOT_`
environment variables. Current safety-relevant settings include:

- `api_key_id`
- `private_key_path`
- `order_submission_enabled`, defaulting to `False`
- `order_cancellation_enabled`, defaulting to `False`
- `demo_market_ticker`, required for the normal lifecycle
- `demo_quote_quantity`, required and strictly greater than zero
- `demo_max_cycles`, defaulting to `1` and strictly greater than zero
- `demo_poll_interval_seconds`, defaulting to `0` and never negative
- Demo-order ticker, count, and price settings

`.env.example` documents the action flags and bounded lifecycle controls. The
real `.env`, full-access demo credential, and RSA private key remain outside
version control.

Structlog produces readable development logs and JSON production logs. Current
execution-related events include `dry_run_execution_planned`,
`execution_plan_reconciled`, `order_cancellation_disabled`,
`order_cancellation_completed`, `demo_order_command_ready`,
`demo_order_created`, and `demo_order_command_completed`.

### Authentication and API client

The bot loads a PEM-formatted RSA private key and signs authenticated Kalshi
requests with RSA-PSS and SHA-256. Query parameters are excluded from the
signed path, matching Kalshi's authentication rules.

`KalshiClient` supports configured single-market lookup and market-list
retrieval, plus order-book, recent-trade, balance, position, individual-order,
and paginated resting-order retrieval. It also supports event-order creation
and individual event-order cancellation. The client targets Kalshi's demo REST
environment. Tests use mocks or `httpx.MockTransport`; they do not contact
Kalshi.

### Market-data boundary, strategy, and risk

Pydantic models parse Kalshi fixed-point strings into `Decimal` values and
timestamps into typed `datetime` values.

`build_market_snapshot()` converts exchange-specific responses into immutable
internal models. It sorts YES bids, converts NO bids into implied YES asks,
filters trades by ticker, and accepts a caller-provided observation time for
deterministic testing.

`decide_quotes()` is pure and deterministic. It requires a complete two-sided
YES book, joins the best bid and implied ask, uses an explicit quantity, and
produces no quote for incomplete books.

`evaluate_quote_risk()` is pure and deterministic. It rejects incomplete
quotes, quantities above the configured maximum, and zero or negative limits.
It does not yet enforce portfolio exposure, available balance, inventory skew,
loss, market status, or stale-data limits.

### Planning, submission, cancellation, and reconciliation

`create_execution_plan()` converts an approved two-sided quote into immutable
internal `BUY` and `SELL` intents. Rejected risk decisions create an empty
plan.

`submit_execution_plan()` returns without API calls when submission is
disabled, maps internal sides to Kalshi values, generates unique client order
IDs, submits sequentially, and tracks successful submissions. If a later
submission fails, it cancels successful earlier orders in reverse order. It
preserves the submission exception when cleanup succeeds and raises an
`ExceptionGroup` when cleanup also fails.

`retrieve_all_resting_orders()` follows pagination until the cursor is empty,
returns an immutable tuple, and rejects a repeated cursor.
`cancel_all_resting_orders()` returns safely when disabled, attempts every
cancellation even when one fails, and raises an `ExceptionGroup` for
cancellation failures.

`reconcile_execution_plan()` reads resting orders for the configured ticker,
compares them against the desired execution plan, cancels unwanted owned orders
when enabled, and submits only missing intents when enabled. It completes all
requested cancellations before reporting aggregated cancellation failures.

`kalshi_bot.cancel_orders` remains an independent command-line kill switch.
When enabled, it loads credentials, opens an authenticated async client,
cancels all resting orders, and logs the canceled count. It cannot undo
contracts that filled before the cancellation request arrived.

### Bounded single-market lifecycle

The normal application now targets an explicitly configured market ticker
instead of selecting the first market returned by the API. It requires an
explicit, positive quote quantity.

`run_demo_lifecycle()` runs a bounded number of cycles, defaulting to one. It
waits only between cycles and never after the final cycle. Each run creates one
unique `kbot-...` session prefix and uses it for every client order ID
submitted during that run.

Reconciliation considers only resting orders with the active session prefix.
This prevents the lifecycle from canceling manual orders or orders owned by a
different bot run. A Python `finally` block—equivalent to C# `finally`—runs
session-scoped cleanup after normal completion or a lifecycle error. It cancels
only orders whose `client_order_id` matches that run's prefix, and only when
cancellation is explicitly enabled.

### Controlled demo-order verification

`kalshi_bot.demo_order` is intentionally separate from the normal lifecycle.
It requires **both** submission and cancellation flags to be enabled, then:

1. Creates one tightly limited, post-only demo order.
2. Logs both the local `client_order_id` and Kalshi's returned exchange
   `order_id`.
3. Immediately cancels the returned exchange `order_id`.
4. Logs completion and closes the HTTP client.

The command deliberately does **not** use `get_order()`. Live testing showed
that a single-order GET returned `404 Not Found` for an event-order ID, while
the create and cancellation event-order endpoints worked together. The
successful create response is therefore the creation verification record, and
the immediate cancellation response verifies cleanup.

Final Day 17 live result:

```text
POST /portfolio/events/orders                 -> 201 Created
DELETE /portfolio/events/orders/{order_id}    -> 200 OK
demo_order_command_completed                  -> logged
```

No GET request occurred and no traceback was raised.

## Safety posture

Implemented safeguards:

- Kalshi demo environment is used.
- Submission and global cancellation have separate fail-closed flags.
- Both flags default to `False`.
- The normal lifecycle requires a configured market ticker and positive quote
  quantity.
- The normal lifecycle is bounded; it defaults to one cycle.
- The normal application cannot submit unless submission is explicitly enabled.
- The session-cleanup path cannot cancel unless cancellation is explicitly
  enabled.
- The global kill-switch command cannot cancel unless cancellation is explicitly
  enabled.
- Session cleanup and lifecycle reconciliation operate only on orders whose
  client order IDs belong to the active bot session.
- Order requests default to post-only and cancel-on-pause behavior.
- Partial submission triggers reverse-order cleanup.
- Cleanup and global cancellation attempt all relevant cancellations.
- Multi-error failures remain observable through `ExceptionGroup`.
- HTTP clients use `async with` and close automatically.
- All write-path tests are mocked; the isolated Day 17 demo was an intentional,
  bounded manual action.

Important remaining limitations:

- A cancellation may arrive after an order partially or fully fills.
- There are no balance, inventory, per-market exposure, portfolio exposure,
  drawdown, or daily-loss protections.
- There is no market-status or stale-data gate.
- There is no retry, rate-limit, or transient-network policy.
- There is no durable state or restart recovery.
- There is no production deployment, alerting, or completed demo soak test.

## Testing

The latest complete local suite passed with **165 test cases**.

The current tests cover:

- Typed API model parsing and client request boundaries, including configured
  single-market lookup.
- Configuration defaults, environment loading, and fail-closed validation of
  ticker, quantity, cycles, and polling interval.
- Pure market-data, strategy, risk, and execution-planning behavior.
- Pagination, cancellation, partial-submission cleanup, and multi-error
  observability.
- Reconciliation behavior: cancel stale owned orders, submit only missing
  intents, preserve matching orders, and avoid replacing when cancellation
  fails or is disabled.
- Bounded-loop behavior: exact cycle count, delay only between cycles, shared
  session prefix, cleanup on normal completion, and cleanup on lifecycle error.
- Session cleanup behavior: cancel session-owned orders only.
- Controlled demo-order request construction and immediate cancellation.

## Quality gate

The final Day 19 quality gate passed:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
```

Expected results:

- Ruff reports all checks passed.
- Ruff formatting check completes successfully.
- pytest reports `165 passed`.

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
| 15 | Connected submission to `main.py` behind the disabled flag and submission-result logging | 83 |
| 16 | Resting-order pagination, cancel-all service, independent kill switch, and cancellation logging | 101 |
| 17 | Isolated full-access demo command, corrected event-order ID handling, create-to-cancel lifecycle, mocked coverage, and live verification | 124 |
| 18 | Resting-order reconciliation, lifecycle cancellation/submission behavior, and `main.py` lifecycle integration | 148 |
| 19 | Bounded configured single-market lifecycle, session-owned reconciliation, and shutdown cleanup | 165 |

## Remaining development

### Milestone 1: reliable bounded demo lifecycle

Estimated remaining work: **2–4 focused development days**.

1. Add market-status and stale-data gates before each execution plan.
2. Add balance, inventory, per-market exposure, portfolio exposure, and loss
   limits.
3. Add timeout, retry, exponential-backoff, and rate-limit handling.
4. Add cycle summaries, error alerts, fault-injection tests, and a deliberately
   bounded live demo exercise.

At this milestone, the bot can run one demo market for a deliberately limited
period with the core safety gates needed for supervised observation. It is not
yet safe for unattended real-money operation.

### Milestone 2: reliable unattended demo operation

Estimated additional work: **4–7 development days** after Milestone 1.

- Add startup recovery and reconciliation drills.
- Add durable order and fill tracking across restarts.
- Add extended demo soak tests and review partial-fill behavior.
- Add operational alerts and runbooks.

### Milestone 3: small live-money pilot

Estimated additional work: **5–10 development days**, plus a deliberate demo
soak period, after Milestone 2.

- Add hard daily-loss and total-exposure circuit breakers.
- Add deployment, monitoring, and credential-rotation procedures.
- Test the kill switch from the deployed environment.
- Start with one market, minimum size, short sessions, and supervision.

## Overall progress estimate

- **About 90–95% complete** toward a bounded, supervised single-market demo
  bot.
- **About 65–75% complete** toward a reliable unattended demo bot.
- **About 50–60% complete** toward a responsibly supervised live-money pilot.

The foundation now includes typed data, authentication, strategy, risk,
planning, reconciliation, submission, cleanup, cancellation, a manually
verified demo write path, bounded lifecycle orchestration, ownership isolation,
logging, and tests. The remaining work is primarily protective risk controls,
recovery, observability, and operational validation.

## Next checkpoint

Day 20 should add the missing safety gates before any longer-running demo
session: market status, stale-data limits, balance and exposure limits, plus a
clearly bounded live demo exercise. Both action flags remain disabled by
default.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue using incremental TDD checkpoints.
- The user manually types project code.
- Bundle routine formatting, linting, and full-suite commands when practical.
- Do not advance a write-capable checkpoint until the preceding safety and test
  foundation passes.


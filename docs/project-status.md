# Kalshi Bot Project Status

_Updated: August 11, 2026 — Day 17 complete_

## Executive summary

The bot has a complete, typed path from Kalshi market data to a flag-gated
order-submission boundary, an independent cancel-all command, and a separately
invoked demo-order lifecycle verified in Kalshi's demo environment.

Current application flow:

`Kalshi API -> typed API models -> MarketSnapshot -> QuoteDecision -> RiskDecision -> ExecutionPlan -> flag-gated submission -> structured logs`

Emergency cancellation flow:

`cancel_orders command -> retrieve every resting-order page -> cancel every resting order -> structured completion log`

Controlled demo-order flow:

`demo_order command -> create one minimum post-only demo order -> log exchange order ID -> cancel immediately -> completion log`

Day 17 is complete. The full local suite passed with **124 tests**, and Ruff's
lint and formatting checks passed. The controlled demo command successfully
created a demo order (`201 Created`) and immediately cancelled it
(`200 OK`), with no GET request and no traceback.

The normal bot remains unable to submit or cancel unless its separate safety
flags are explicitly enabled. Both flags remain `false` in the private
`.env` outside controlled testing.

## Environment

- Windows and PowerShell
- Cursor
- Python 3.14.6
- uv for dependency management
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
environment variables. Safety-relevant settings include:

- `api_key_id`
- `private_key_path`
- `order_submission_enabled`, defaulting to `False`
- `order_cancellation_enabled`, defaulting to `False`
- Demo-order ticker, count, and price settings

`.env.example` documents both action flags as disabled. The real `.env`,
full-access demo credential, and RSA private key remain outside version control.

Structlog supports readable development logs and JSON production logs. Current
execution events include `dry_run_execution_planned`,
`execution_submission_evaluated`, `order_cancellation_disabled`,
`order_cancellation_completed`, `demo_order_command_ready`,
`demo_order_created`, and `demo_order_command_completed`.

### Authentication and API client

The bot loads a PEM-formatted RSA private key and signs authenticated Kalshi
requests with RSA-PSS and SHA-256. Query parameters are excluded from the
signed path, matching Kalshi authentication rules.

`KalshiClient` supports market, order-book, recent-trade, balance, and
position retrieval; event-order creation; individual event-order cancellation;
and paginated resting-order retrieval. It targets Kalshi's demo REST
environment. Tests use mocks or `httpx.MockTransport`; they do not contact
Kalshi.

### Market-data boundary, strategy, and risk

Pydantic models parse Kalshi fixed-point strings into `Decimal` values and
timestamps into typed `datetime` values.

`build_market_snapshot()` converts exchange-specific responses into immutable
internal models: it sorts YES bids, converts NO bids to implied YES asks,
filters trades by ticker, and supports a caller-provided observation time for
deterministic testing.

`decide_quotes()` is pure and deterministic. It requires a complete two-sided
YES book, joins the best bid and implied ask, uses an explicit quantity, and
produces no quote for incomplete books.

`evaluate_quote_risk()` is pure and deterministic. It rejects incomplete
quotes, quantities above the configured maximum, and zero or negative limits.
It does not yet enforce portfolio exposure, available balance, inventory skew,
loss, market status, or stale-data limits.

### Planning, submission, and cancellation

`create_execution_plan()` converts an approved two-sided quote into immutable
internal `BUY` and `SELL` intents; rejected risk decisions create an empty
plan.

`submit_execution_plan()` returns without API calls when submission is
disabled, maps internal sides to Kalshi values, generates unique UUID client
order IDs, submits sequentially, and tracks only successful submissions. If a
later submission fails, it cancels successful earlier orders in reverse order.
It preserves the submission exception when cleanup succeeds and raises an
`ExceptionGroup` when cleanup also fails.

`retrieve_all_resting_orders()` follows pagination until the cursor is empty,
returns an immutable tuple, and rejects a repeated cursor. The
`cancel_all_resting_orders()` service returns safely when disabled, attempts
every cancellation even when one fails, and raises an `ExceptionGroup` for
cancellation failures.

`kalshi_bot.cancel_orders` is an independent command-line kill switch. When
enabled, it loads credentials, opens an authenticated async client, cancels all
resting orders, and logs the canceled count. It cannot undo contracts that
filled before the cancellation request arrived.

### Controlled demo-order verification

`kalshi_bot.demo_order` is intentionally separate from the normal bot loop.
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
- The normal application cannot submit unless submission is explicitly enabled.
- The kill-switch cannot cancel unless cancellation is explicitly enabled.
- The demo command requires both flags, is separate from the normal loop, and
  immediately cancels the order it creates.
- Order requests default to post-only and cancel-on-pause behavior.
- Partial two-order submission triggers reverse-order cleanup.
- Cleanup and global cancellation attempt all relevant cancellations.
- Multi-error failures remain observable through `ExceptionGroup`.
- HTTP clients use `async with` and close automatically.
- All write-path tests are mocked; the isolated Day 17 demo was an intentional,
  bounded manual action.

Remaining limitations:

- A cancellation may arrive after an order partially or fully fills.
- There is no continuous open-order reconciliation loop.
- There are no inventory, exposure, drawdown, or daily-loss protections.
- There is no stale-market-data or closed-market gate.
- There is no retry, rate-limit, or transient-network policy.
- There is no durable state, restart recovery, production deployment, or alerts.

## Testing and quality gate

The latest complete local suite passed with **124 tests**.

Demo-order tests cover disabled execution, both flag requirements, safe async
client setup and cleanup, request construction, the
`create -> cancel -> return create response` lifecycle, cancellation with the
exchange `order_id` rather than the local ID, no `get_order()` call,
cancellation failures, and flat `CreateOrderResponse` completion logging.

Final Day 17 validation passed:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run python -m pytest
```

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

## Remaining development

### Milestone 1: bounded single-market demo lifecycle

Estimated remaining work: **2–4 focused development days**.

1. Add a bounded single-market quote lifecycle: retrieve market data, decide,
   risk-check, reconcile, submit or replace, and cancel during graceful
   shutdown.
2. Reconcile desired quotes against actual resting orders so duplicates are not
   blindly created.
3. Make maximum cycles, polling interval, quantity, ticker, and both action
   flags explicit and fail-closed.
4. Add graceful shutdown that cancels the bot's own resting orders.

At this milestone, the bot can operate on one demo market for a bounded period.
It is not yet safe for unattended real-money operation.

### Milestone 2: reliable unattended demo operation

Estimated additional work: **5–8 development days** after Milestone 1.

- Add balance, inventory, per-market exposure, portfolio exposure, and loss
  limits.
- Add market-status, stale-data, spread, and fee/profitability gates.
- Add timeout, retry, exponential-backoff, and rate-limit handling.
- Add startup recovery and reconciliation drills.
- Add cycle summaries, error alerts, fault-injection tests, and extended demo
  soak tests.

### Milestone 3: small live-money pilot

Estimated additional work: **5–10 development days**, plus a deliberate demo
soak period, after Milestone 2.

- Add durable order and fill reconciliation across restarts.
- Add hard daily-loss and total-exposure circuit breakers.
- Add deployment, monitoring, alerts, and operational runbooks.
- Test credential rotation and kill-switch operation from deployment.
- Start with one market, minimum size, short sessions, and supervision.

## Overall progress estimate

- **About 85–90% complete** toward a bounded, operational single-market demo bot.
- **About 60–70% complete** toward a reliable unattended demo bot.
- **About 45–55% complete** toward a responsibly supervised live-money pilot.

The foundation is complete: typed data, authentication, strategy, risk,
planning, submission, cleanup, cancellation, a manually verified demo write
path, logging, and tests all have explicit boundaries. Remaining work is
continuous order-lifecycle management, broader risk control, recovery,
observability, and operational validation.

## Next checkpoint

Day 18 should define reconciliation behavior in tests before writing the
bounded single-market loop. Both action flags remain disabled by default, and
the normal bot loop must remain safe when either flag is disabled.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue using incremental TDD checkpoints.
- The user manually types project code.
- Bundle routine formatting, linting, and full-suite commands when practical.
- Do not advance a write-capable checkpoint until the preceding safety and test
  foundation passes.


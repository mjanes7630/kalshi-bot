# Kalshi Bot Project Status

_Updated: August 18, 2026 — Day 24 complete_

## Executive summary

The bot now has a typed, tested path from Kalshi demo-market data through quote strategy, risk checks, execution planning, reconciliation, inventory safety, bounded lifecycle cleanup, restart cleanup recovery, and independent read-only health verification.

`Kalshi API -> typed API models -> MarketSnapshot -> QuoteDecision -> position + balance risk gates -> ExecutionPlan -> session-scoped reconciliation -> inventory flattening -> flag-gated execution -> bounded polling -> session cleanup -> structured logs`

Day 24 adds a shared authenticated-client lifetime model, lifecycle state recovery, and an independently runnable market health check. The latest complete local suite passes with **262 tests**. Ruff formatting and linting pass. Order submission and cancellation remain disabled by default in the private `.env`.

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
  api/                 # Authentication, shared client session, typed HTTP client, API models
  execution/           # Plans, submission, cancellation, reconciliation, lifecycle state/recovery
  marketdata/          # Exchange-to-domain snapshot boundary
  models/              # Internal market model
  risk/                # Pure risk decisions and checks
  strategy/            # Pure quote decisions
  cancel_orders.py
  config.py
  demo_order.py
  health.py
  health_check.py
  logging_config.py
  main.py

tests/                 # Unit and lifecycle integration tests
```

## Current implementation

### Configuration and logging

`Settings` loads typed configuration from `.env` and `KALSHI_BOT_` environment variables. Separate submission and cancellation flags both default to `False`. The lifecycle uses one configured market, a positive quote quantity, a bounded cycle count, and a polling interval.

Risk settings include a maximum market-data age, projected per-market-exposure cap, projected available-balance floor, and inventory-flattening controls. Credentials and private keys remain outside version control.

### Shared authenticated client sessions

`authenticated_kalshi_client(settings)` in `kalshi_bot.api.session` is the single owner of authenticated client construction. It validates configured credentials, loads the RSA private key, opens an `httpx.AsyncClient`, creates a typed `KalshiClient`, yields it to one top-level operation, and closes the HTTP client whether that operation succeeds or raises.

Each top-level command receives its own independent client instance when launched, but no command duplicates the authentication or HTTP setup:

- `run_demo_lifecycle()` owns one client for recovery, every cycle, and final cleanup.
- `run_demo_market_health_check()` owns one client for one read-only health-check run.
- `run_demo_order()` owns one client for its isolated create-and-cancel verification.
- `run_order_cancellation()` owns one client for the independently gated kill-switch run.

### API client and market-data boundary

The client uses RSA-PSS/SHA-256 to sign authenticated Kalshi demo requests. It supports market lookup, order books, trades, balance, positions, single-order and paginated resting-order reads, event-order creation, and cancellation.

Typed Pydantic models convert fixed-point API values to `Decimal`. Market API statuses use `KalshiMarketStatus`, including `ACTIVE` for an open-for-trading market. Returned orders distinguish their contract leg (`yes`/`no`) from their book side (`bid`/`ask`), so reconciliation can correctly identify resting orders after live API reads. `build_market_snapshot()` creates the immutable domain snapshot consumed by the strategy and risk layers.

#### Read-only retry policy

All GET methods use one bounded retry helper:

- Up to three total attempts: the original request and two retries.
- Retries `httpx.TransportError` failures such as connection loss and timeouts.
- Retries `HTTPStatus.TOO_MANY_REQUESTS` (`429`) responses.
- Uses exponential fallback waits of 0.1 then 0.2 seconds.
- Honors a valid non-negative numeric `Retry-After` header on a `429`.
- Leaves all other HTTP responses to the calling method's `response.raise_for_status()` handling.

Order-creation and cancellation methods deliberately do **not** retry. A timed-out POST or DELETE may have been processed by Kalshi; resending it could create an ambiguous or duplicate action.

### Strategy, risk, and inventory safety

`decide_quotes()` is pure and deterministic. It requires a complete, non-crossed two-sided YES book and produces a bid and ask at the configured quantity. An incomplete, zero-spread, or crossed book produces no quote.

`evaluate_quote_risk()` requires an open, fresh market and checks projected per-market exposure and available balance before an execution plan can contain new quotes. Quote reservation conservatively assumes both proposed sides can expose the account at once.

When reconciliation identifies open YES inventory that should be removed, it cancels the relevant resting quote before submitting the flattening intent. Long YES inventory is flattened by selling YES; short YES inventory is flattened by buying YES. This prevents a resting quote from increasing the directional position while the bot is trying to remove it.

### Planning, execution, cancellation, and reconciliation

`create_execution_plan()` maps approved quotes to immutable intents. `submit_execution_plan()` is disabled unless explicitly enabled, uses unique client order IDs, and cleans up earlier successful submissions in reverse order if a later submission fails. Multiple failures remain visible through `ExceptionGroup`.

Resting-order retrieval is paginated and rejects repeated cursors. Reconciliation considers only session-owned client order IDs, cancels unwanted orders, preserves matching desired orders, submits missing intents, and does not replace a quote when prerequisite cancellation fails or is disabled.

The independent `cancel_orders` command remains a separately gated kill switch. It cannot reverse an order that has already filled.

### Bounded lifecycle, restart recovery, and controlled demo order

`run_demo_lifecycle()` runs the configured market for a bounded cycle count and waits only between cycles. Every run has one shared `kbot-...` session prefix. `retrieve_demo_api_data()` obtains market data, positions, and balance before risk evaluation and reconciliation.

Before its first cycle, the lifecycle persists the active session prefix and ticker. On the next startup, recovery uses that record to locate and cancel only resting orders owned by the interrupted session before beginning a new session. State is cleared only after successful cleanup; failed cleanup preserves it for a later recovery attempt. This provides restart cleanup recovery for known resting session orders, not a complete durable record of fills or account positions.

A lifecycle cancellation or another `BaseException` still triggers session-scoped cleanup. If both the lifecycle and cleanup fail, both failures are preserved in an `ExceptionGroup` or `BaseExceptionGroup` instead of allowing cleanup to hide the original failure. `kalshi_bot.demo_order` remains a separate, intentionally limited create-and-immediately-cancel verification command.

### Read-only market health check

`check_market_health()` retrieves one configured market and returns an immutable `MarketHealth` result containing the returned ticker, Kalshi market status, and an `is_healthy` flag. Only `ACTIVE` is healthy for trading.

`run_market_health_check()` logs a successful active result at `info`, a reachable but non-active result at `warning`, and an HTTP/API failure at `error` before re-raising it. This preserves the operational distinction between “Kalshi responded but the market cannot trade” and “the current Kalshi state is unknown because the request failed.”

The standalone command is:

```powershell
uv run python -m kalshi_bot.health_check
```

On Day 24 it was verified live against the configured demo market:

```text
market_health_check_completed
is_healthy=True
market_status=active
ticker=KXLLM1-26DEC31-A
```

No order was placed, cancelled, or modified by that verification.

## Safety posture

Implemented safeguards:

- Demo environment only; write paths are disabled by default.
- Open-market, fresh-observation, exposure, and available-balance gates.
- Conservative two-sided quote reservation.
- Post-only and cancel-on-pause order behavior.
- Inventory flattening cancels conflicting resting quotes first.
- Session-scoped reconciliation, cleanup, and restart cleanup recovery.
- Independently gated global cancellation.
- Reverse-order cleanup after partial submission failure.
- Aggregated cancellation failures through `ExceptionGroup`.
- Bounded retries only for idempotent read requests.
- Explicit no-retry protection for order creation and cancellation.
- Typed, mocked tests around all write-capable behavior.
- Typed Kalshi market-status and returned-order response contracts.
- Crossed-book quote refusal.
- Safe HTTP error diagnostics.
- Shared authenticated-client construction and guaranteed HTTP cleanup.
- Independently runnable read-only market health verification.

Important remaining limitations:

- A cancellation or flattening order can still arrive after a partial or full fill.
- Lifecycle state is not a full durable fill, position, or account-event ledger.
- There are no portfolio-wide exposure, drawdown, or daily-loss circuit breakers.
- There is no alerting, deployment, or completed sustained demo soak test.
- Only `429` response-rate limiting is retried; other HTTP error responses are intentionally surfaced immediately for now.

## Testing and quality gate

The latest full suite passed with **262 tests**.

Coverage includes typed API models and request boundaries, configuration validation, market-data building, quote decisions, risk gates, inventory flattening, pagination, cancellation, partial-submission cleanup, reconciliation, bounded lifecycle behavior, session cleanup, controlled demo-order flow, and read-only retry behavior.

Day 24 additionally covers:

- lifecycle-state persistence, clearing, and recovery behavior;
- shared-client ownership for lifecycle, health check, demo order, and kill-switch commands;
- authenticated-client setup, successful cleanup, and cleanup when work raises;
- active and non-active market health evaluation;
- health-check logging for successful, non-active, and failed API requests;
- standalone health-command validation and entry-point wiring.

Final Day 24 validation:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run python -m pytest
```

Expected result: Ruff formatting and lint checks complete successfully, and pytest reports `262 passed`.

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
| 23 | Operational observability, API-contract hardening, crossed-book safety, and supervised demo lifecycle verification | 232 |
| 24 | Restart cleanup recovery, shared authenticated-client sessions, and independent market health check | 262 |

## Agreed next-phase roadmap

The project will continue as a single-market system until the single-market demo and live operational controls have proved reliable. GUI work and multi-market foundation work may proceed in parallel, but neither may alter the frozen soak-test or live single-market release without its own review, tests, and release.

### Phase 1: automated demo readiness

Target: **August 18–24, 2026**.

- Complete restart-recovery drills, alerting, deployment procedures, and the dedicated-PC soak-test checklist.
- Retain one configured demo market and all existing fail-closed execution flags.

### Phase 2: frozen single-market demo soak

Target release: **`v0.1.0-demo-soak` on August 25, 2026**.

- Deploy the exact tagged release to a separate PC.
- Run one configured demo market continuously for an extended period.
- Treat the soak deployment as immutable: update it only for a verified safety, reliability, or correctness issue, then cut and redeploy a new tagged release.
- Record uptime, restarts, errors, cleanup results, and release-specific outcomes.

### Phase 3: parallel feature branches

While the demo soak runs, development can proceed independently on:

- `feature/gui-dashboard`: a demo-tested GUI for bounded configuration, status, structured logs, start/stop control, and visible safety switches. It must not bypass validation, risk checks, or explicit execution flags.
- `feature/multi-market-foundation`: architecture and tests for portfolio-wide exposure, balance reservation, persistent state, market selection, and rate-limit budgeting. This branch does **not** activate multiple markets.

`main` remains the tested single-market integration branch. The soak PC remains on the tagged release rather than tracking `main` or either feature branch.

### Phase 4: supervised single-market live trial

Entry criteria: a clean demo soak, validated operations/runbook, and a demo-tested GUI if it is included in the release.

- Create a new approved single-market release from tested code.
- Use one market, minimum practical limits, active monitoring, and an immediate stop path.
- Keep credentials outside source control and retain exclusive control of enabling live orders.
- Fix any issue through the normal branch, test, release, and redeployment process; do not patch the running machine ad hoc.

### Phase 5: automated single-market live operation

After a stable supervised live trial, prove that the bot can run with minimal intervention while preserving monitoring, restart recovery, alerting, reconciliation, and stop controls.

### Phase 6: multi-market rollout

Only after stable single-market live operation:

1. Run supervised multi-market testing in the demo environment.
2. Validate portfolio-wide limits, state recovery, rate-limit behavior, and operational visibility.
3. Begin a tightly limited, carefully monitored multi-market live trial.

## Optimistic calendar targets

These dates are planning targets, not permission to skip a safety gate.

| Target date | Planned outcome |
|---|---|
| August 24, 2026 | Automated demo readiness complete |
| August 25, 2026 | `v0.1.0-demo-soak` deployed to dedicated PC |
| September 7, 2026 | Two-week clean demo soak and GUI MVP target |
| September 14, 2026 | Multi-market foundation target complete |
| September 8–21, 2026 | Supervised tiny-limit single-market live trial target |
| September 22–October 5, 2026 | Automated single-market live-operation target |
| October 6–26, 2026 | Supervised multi-market demo target |
| October 27, 2026 onward | Earliest careful multi-market live-trial target |

## Overall progress estimate

- **100% complete** toward a bounded, supervised single-market demo.
- **78–85% complete** toward a reliable unattended single-market demo bot.
- **60–70% complete** toward a responsibly supervised single-market live-money pilot.

## Working preferences

- Explain Python concepts through C# comparisons where useful.
- Explain every PowerShell command, argument, operator, and symbol.
- Continue with incremental TDD checkpoints and identify each test type.
- The user manually types project code.
- Do not advance a write-capable checkpoint until the preceding safety and test foundation passes.

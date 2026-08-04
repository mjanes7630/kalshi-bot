# Kalshi Bot Project Status

## Environment

- Windows
- Cursor
- Python 3.14.6
- uv for dependency management
- pytest for testing
- Ruff for linting and formatting
- Pydantic for API-response validation
- HTTPX for asynchronous HTTP requests
- Cryptography for RSA request signing
- GitHub repository configured
- Cursor launch configuration runs `kalshi_bot.main` as a module

## Project structure

- `kalshi_bot/api/__init__.py`
- `kalshi_bot/api/auth.py`
- `kalshi_bot/api/client.py`
- `kalshi_bot/api/models.py`
- `kalshi_bot/marketdata/__init__.py`
- `kalshi_bot/marketdata/builder.py`
- `kalshi_bot/marketdata/models.py`
- `kalshi_bot/risk/__init__.py`
- `kalshi_bot/risk/checks.py`
- `kalshi_bot/risk/models.py`
- `kalshi_bot/strategy/__init__.py`
- `kalshi_bot/strategy/models.py`
- `kalshi_bot/strategy/quotes.py`
- `kalshi_bot/config.py`
- `kalshi_bot/logging_config.py`
- `kalshi_bot/main.py`
- `kalshi_bot/models/market.py`
- `tests/test_api_client.py`
- `tests/test_api_models.py`
- `tests/test_auth.py`
- `tests/test_config.py`
- `tests/test_logging_config.py`
- `tests/test_market.py`
- `tests/test_marketdata_builder.py`
- `tests/test_marketdata_models.py`
- `tests/test_risk_checks.py`
- `tests/test_strategy_quotes.py`
- `.vscode/launch.json`
- `.env.example`
- `.gitignore`
- `pyproject.toml`
- `uv.lock`

## Current implementation

### Market model

`Market` is a dataclass containing:

- `ticker`
- `title`
- `best_bid`
- `best_ask`
- `recent_trade_prices`

It provides methods for:

- Spread calculation
- Midpoint calculation
- Average trade-price calculation

Validation runs through `__post_init__`.

Prices:

- Use `Decimal` dollar values instead of integer cents
- Must be instances of `Decimal`
- Must be between `Decimal("0")` and `Decimal("1")`
- Best bid cannot exceed best ask
- Empty trade lists are allowed, but calculating their average raises `ValueError`

### Authentication

`kalshi_bot/api/auth.py` contains the authentication helpers required for
signed Kalshi requests.

Current behavior:

- Loads a PEM-formatted RSA private key from a configured file path
- Accepts private-key files regardless of filename extension
- Verifies that the loaded key is an RSA private key
- Removes query parameters from the path before signing
- Converts the HTTP method to uppercase before signing
- Signs the timestamp, method, and path with RSA-PSS and SHA-256
- Base64-encodes the generated signature
- Creates the three required Kalshi authentication headers

Authentication tests use temporary generated keys and do not access the real
demo credentials.

### API response models

`kalshi_bot/api/models.py` contains typed Pydantic models for Kalshi market,
order-book, trade, balance, and position responses.

`KalshiMarket` currently includes:

- `ticker`
- `title`
- `yes_bid_dollars`
- `yes_ask_dollars`
- `no_bid_dollars`
- `no_ask_dollars`
- `last_price_dollars`

`GetMarketsResponse` contains:

- A list of `KalshiMarket` objects
- The pagination cursor

The order-book response models contain:

- Fixed-point YES price-and-quantity levels
- Fixed-point NO price-and-quantity levels

`KalshiTrade` currently includes:

- `trade_id`
- `ticker`
- `count_fp`
- `yes_price_dollars`
- `no_price_dollars`
- `created_time`
- `is_block_trade`

`GetTradesResponse` contains:

- A list of `KalshiTrade` objects
- The pagination cursor

`GetBalanceResponse` currently includes:

- `balance`
- `balance_dollars`
- `portfolio_value`
- `updated_ts`

`KalshiMarketPosition` currently includes:

- `ticker`
- `total_traded_dollars`
- `position_fp`
- `market_exposure_dollars`
- `realized_pnl_dollars`
- `fees_paid_dollars`
- `last_updated_ts`

`KalshiEventPosition` currently includes:

- `event_ticker`
- `total_cost_dollars`
- `total_cost_shares_fp`
- `event_exposure_dollars`
- `realized_pnl_dollars`
- `fees_paid_dollars`

`GetPositionsResponse` contains:

- A list of `KalshiMarketPosition` objects
- A list of `KalshiEventPosition` objects
- The pagination cursor

Pydantic converts Kalshi's fixed-point strings into `Decimal` values and ISO
8601 timestamps into timezone-aware `datetime` values. Unknown response fields
are ignored so Kalshi can return additional fields without breaking the client.

### API client

`kalshi_bot/api/client.py` contains the asynchronous, read-only
`KalshiClient`.

Current behavior:

- Accepts an injected `httpx.AsyncClient`
- Targets Kalshi's demo REST environment
- Accepts optional API-key and RSA private-key credentials
- Sends a public `GET /markets` request
- Supports market pagination through `limit` and optional `cursor` parameters
- Sends an authenticated `GET /markets/{ticker}/orderbook` request
- Supports order-book depths from `0` through `100`
- Sends a public `GET /markets/trades` request
- Supports optional trade `ticker` and `cursor` filters
- Supports trade limits from `1` through `1000`
- Sends an authenticated `GET /portfolio/balance` request
- Sends an authenticated `GET /portfolio/positions` request
- Supports optional position `ticker`, `event_ticker`, and `cursor` filters
- Supports position limits from `1` through `1000`
- Omits unset optional query parameters instead of sending empty values
- Excludes query parameters from authenticated request signatures
- Generates the required millisecond Unix timestamp
- Raises `ValueError` for invalid limits or depths
- Raises `ValueError` when a protected request is attempted without credentials
- Raises `httpx.HTTPStatusError` for unsuccessful responses
- Validates successful JSON responses through typed Pydantic models
- Does not place orders

The injected HTTP client keeps the API boundary testable with mocked requests.
Public market and trade requests do not require credentials.

### Internal market-data models

`kalshi_bot/marketdata/models.py` contains immutable, strategy-ready domain
models that are independent of Kalshi's API response format.

`OrderBookLevel` contains:

- `price`
- `quantity`

`MarketTrade` contains:

- `trade_id`
- `price`
- `quantity`
- `created_time`
- `is_block_trade`

`MarketSnapshot` contains:

- `ticker`
- `title`
- `last_price`
- Immutable YES bid levels
- Immutable YES ask levels
- Immutable recent trades
- `observed_at`

`MarketSnapshot` provides read-only properties for:

- Best YES bid
- Best YES ask
- YES spread
- YES midpoint

The best bid and ask properties return `None` when their side of the order book
has no liquidity. Spread and midpoint also return `None` unless both sides are
available. This lets the bot represent real empty or one-sided books safely.

The models use `@dataclass(frozen=True)` and tuples so a completed snapshot
cannot be changed accidentally after it is handed to strategy code. This is
similar in purpose to immutable C# records containing read-only collections.

### Market-snapshot builder

`kalshi_bot/marketdata/builder.py` is the translation boundary between Kalshi's
Pydantic API models and the bot's internal market-data models.

`build_market_snapshot()` currently:

- Accepts a market, its order book, its recent trades, and an observation time
- Copies market metadata into an internal `MarketSnapshot`
- Converts API order-book tuples into typed `OrderBookLevel` objects
- Sorts YES bids from highest price to lowest price
- Derives YES asks from NO bids using `Decimal("1") - no_bid_price`
- Sorts derived YES asks from lowest price to highest price
- Converts matching API trades into immutable `MarketTrade` objects
- Excludes trades whose ticker does not match the snapshot market
- Preserves fixed-point `Decimal` prices and quantities
- Uses the caller-provided `observed_at` timestamp

Kalshi's order-book response supplies YES and NO bids. A NO bid at `0.5600`
represents an implied YES ask at `0.4400`, because the two complementary
contract prices total `1.0000`. The builder performs this exchange-specific
conversion once so future strategy code can work with a conventional YES
bid-and-ask view.

The builder also guarantees best-price-first ordering. As a result, strategy
code can use the first bid and ask levels without knowing how Kalshi ordered the
original response.

Passing `observed_at` into the builder rather than calling `datetime.now()`
inside it keeps the conversion deterministic and easy to test. This is similar
to passing an `IClock` value into a C# domain mapper.

This layer prevents future strategy code from depending directly on Pydantic,
Kalshi field names, or Kalshi's YES/NO order-book representation. If the API
payload changes, the API models and builder can be updated while the strategy
continues consuming the same `MarketSnapshot` interface.

The current data flow is:

`Kalshi JSON -> Pydantic API models -> build_market_snapshot() -> MarketSnapshot -> decide_quotes() -> QuoteDecision -> evaluate_quote_risk() -> RiskDecision -> logging`

### Strategy models

`kalshi_bot/strategy/models.py` contains immutable output models for the bot's
first quoting decision.

`QuoteProposal` contains:

- `price`
- `quantity`

`QuoteDecision` contains:

- `ticker`
- An optional YES bid proposal
- An optional YES ask proposal
- A controlled decision reason
- A derived `should_quote` property

`QuoteDecisionReason` currently supports:

- `TWO_SIDED_BOOK`
- `INCOMPLETE_BOOK`

`QuoteProposal` and `QuoteDecision` use `@dataclass(frozen=True)`, so strategy
results cannot be changed after they are created. This is similar to using
immutable C# records for a decision result.

The bid and ask proposals are optional because a snapshot with missing
liquidity must produce a complete no-quote decision rather than a single-sided
proposal. `should_quote` is `True` only when both proposals exist.

A `QuoteProposal` is not a Kalshi order. It contains only the proposed price
and quantity, has no API request fields, and causes no external action.

### Quote strategy

`kalshi_bot/strategy/quotes.py` contains the pure `decide_quotes()` function.

Current behavior:

- Accepts an immutable `MarketSnapshot`
- Requires `quote_quantity` as an explicit keyword argument
- Reads the snapshot's best YES bid and best YES ask
- Proposes joining both best prices with the requested quantity when both sides exist
- Returns no bid or ask proposal when either order-book side is missing
- Uses `TWO_SIDED_BOOK` for a complete two-sided proposal
- Uses `INCOMPLETE_BOOK` when the strategy safely declines to quote
- Performs no network requests and modifies no state
- Returns the same result for the same inputs

The keyword-only quantity keeps calls self-documenting:

`decide_quotes(snapshot, quote_quantity=Decimal("2.00"))`

The strategy deliberately refuses to produce only one side of a market-making
quote. More advanced pricing, inventory, and fee rules have not been added yet.

### Risk models

`kalshi_bot/risk/models.py` contains the immutable result of the bot's first
risk evaluation.

`RiskDecision` contains:

- `ticker`
- A controlled risk-decision reason
- A derived `approved` property

`RiskDecisionReason` currently supports:

- `APPROVED`
- `INCOMPLETE_QUOTE`
- `QUOTE_SIZE_EXCEEDS_LIMIT`

`RiskDecision` uses `@dataclass(frozen=True)`, so a completed risk result cannot
be changed after evaluation. The `approved` property is `True` only when the
reason is `APPROVED`. This is similar to an immutable C# result record with a
calculated `Approved` property.

### Quote-risk check

`kalshi_bot/risk/checks.py` contains the pure `evaluate_quote_risk()` function.

Current behavior:

- Accepts an immutable `QuoteDecision`
- Requires `max_quote_quantity` as an explicit keyword argument
- Rejects zero and negative maximum quantities with `ValueError`
- Rejects a decision when either the YES bid or YES ask proposal is missing
- Rejects a decision when either proposed quantity exceeds the configured limit
- Treats the maximum quantity as an inclusive limit
- Approves only a complete two-sided quote within the size limit
- Returns an immutable and observable `RiskDecision`
- Performs no network requests and modifies no state
- Returns the same result for the same inputs

The risk layer repeats the completeness check even though strategy already
declines incomplete books. This defense-in-depth boundary prevents future
execution code from trusting an incomplete upstream decision accidentally.

The keyword-only limit keeps calls self-documenting:

`evaluate_quote_risk(quote_decision, max_quote_quantity=Decimal("2.00"))`

This first gate checks proposal completeness and per-side size only. It does
not yet evaluate inventory, portfolio exposure, available balance, fees, or
market-specific limits.

### Application

`main.py`:

- Loads typed settings
- Configures structured logging
- Creates a sample market with `Decimal` prices
- Calculates its spread, midpoint, and average trade price
- Classifies trades as below, at, or above the midpoint
- Loads the configured demo RSA private key
- Creates an authenticated `KalshiClient`
- Retrieves one market from the Kalshi demo environment
- Retrieves up to five order-book levels for the selected market
- Retrieves up to five recent trades for the selected market
- Builds an immutable, strategy-ready `MarketSnapshot`
- Passes the snapshot into the pure quote strategy
- Uses a fixed demo quote quantity of `Decimal("2.00")`
- Produces an immutable `QuoteDecision`
- Passes the quote decision into the pure risk gate
- Uses a fixed maximum quote quantity of `Decimal("2.00")`
- Produces an immutable `RiskDecision`
- Records a timezone-aware UTC observation time
- Reads best bid, best ask, spread, and midpoint from the snapshot
- Retrieves the demo portfolio balance
- Retrieves up to ten portfolio positions
- Logs snapshot metadata, level counts, recent-trade count, balance, and positions
- Logs the quote decision, reason, and optional proposal values
- Logs the risk decision, approval status, reason, and maximum quote quantity
- Handles empty order-book sides by logging `None`
- Safely declines to quote when the order book is incomplete
- Independently rejects incomplete proposals at the risk boundary
- Logs successful and failed demo API-data requests
- Catches expected application, key-loading, and HTTP exceptions
- Uses structured logging instead of `print()`

A live read-only verification successfully retrieved markets, the selected
market's order book, trades, balance, and positions. The selected market had no
current order-book levels or recent trades. The resulting snapshot correctly
reported zero bid levels, zero ask levels, zero recent trades, and `None` for
best bid, best ask, spread, and midpoint instead of failing. The strategy then
returned `INCOMPLETE_BOOK`, logged `should_quote=False`, and left all proposal
fields as `None`. The risk gate independently returned `INCOMPLETE_QUOTE`,
logged `approved=False`, and prevented the decision from proceeding. No orders
were placed.

### Configuration

`config.py` provides a typed `Settings` class.

Current settings include:

- `environment`
- `log_level`
- `api_key_id`
- `private_key_path`

Configuration behavior:

- Uses safe defaults when values are not provided
- Loads local values from `.env`
- Supports `KALSHI_BOT_` environment-variable overrides
- Converts the configured private-key location into a `Path`
- Allows `development` and `production` environments
- Rejects invalid environment values
- `.env` is excluded from Git through `.gitignore`
- `.env.example` documents credential variable names without containing values
- The real private-key file is stored outside the repository

The current demo credential variables are:

- `KALSHI_BOT_API_KEY_ID`
- `KALSHI_BOT_PRIVATE_KEY_PATH`

The configured demo API key is read-only. A separate full-access key will be
created later when order execution is intentionally implemented.

### Logging

`logging_config.py` configures Structlog.

Logging behavior:

- Development uses human-readable console logs
- Production uses JSON logs
- Events include timestamps, log levels, and logger names
- The configured log level filters lower-priority events

Current application events include:

- `application_started`
- `market_analyzed`
- `trade_price_classified`
- `demo_api_data_retrieved`
- `strategy_quotes_decided`
- `quote_risk_evaluated`
- `demo_api_data_retrieval_failed`

## Testing

The test suite currently has 61 passing tests:

- 11 market-model tests
- 4 configuration tests
- 3 logging tests
- 5 API-model tests
- 17 API-client tests
- 3 authentication tests
- 4 market-data-model tests
- 3 market-snapshot-builder tests
- 4 quote-strategy tests
- 7 quote-risk tests

Coverage includes:

- Decimal spread calculation
- Decimal midpoint calculation
- Decimal average trade-price calculation
- Decimal price-type validation
- Prices outside the valid range
- Crossed markets
- Empty trade-list averages
- Parameterized validation cases
- Default configuration values
- `.env` loading
- Credential environment-variable loading
- Private-key path conversion
- Invalid environment rejection
- Development console logging
- Production JSON logging
- Log-level filtering
- Fixed-point market-price parsing
- Fixed-point order-book price-and-quantity parsing
- Fixed-point trade-price and quantity parsing
- Fixed-point balance and position parsing
- ISO 8601 timestamp parsing
- Nested API-response parsing
- Pagination cursor parsing
- Public market request method, path, and query parameters
- Authenticated order-book requests
- Order-book depth validation
- Public trade-history requests
- Trade-limit validation
- Authenticated balance requests
- Authenticated position requests
- Position-limit validation
- Optional query-parameter omission
- Credential requirements for protected requests
- Unsuccessful HTTP response handling
- RSA private-key loading from a file
- RSA-PSS and SHA-256 request signing
- Query-parameter removal before signing
- Required Kalshi authentication headers
- Cryptographic verification of generated request signatures
- Mocked API requests without live network access
- Execution of nested asynchronous test helpers through `asyncio.run()`
- Immutable market-data snapshots
- Best YES bid and ask selection
- Safe handling of empty order-book sides
- Snapshot spread and midpoint calculation
- YES-bid best-price-first ordering
- Conversion of NO bids into implied YES asks
- YES-ask best-price-first ordering
- Market-specific trade filtering and conversion
- Deterministic observation timestamps
- Two-sided quote proposals at the best YES bid and ask
- Explicit fixed-point `Decimal` quote quantities
- Immutable quote-decision output models
- Derived `should_quote` behavior
- Safe no-quote decisions when YES bids are missing
- Safe no-quote decisions when YES asks are missing
- Safe no-quote decisions when the entire order book is empty
- Approval of a complete two-sided quote at the inclusive size limit
- Rejection when the YES bid exceeds the maximum quote quantity
- Rejection when the YES ask exceeds the maximum quote quantity
- Rejection when either quote side is missing
- Derived `approved` behavior for risk decisions
- Zero maximum-quantity validation
- Negative maximum-quantity validation

Run the full test suite with:

`uv run python -m pytest -v`

Command explanation:

- `uv` invokes the project-management tool.
- `run` executes the remaining command inside the project environment.
- `python` starts Python.
- `-m` runs the following installed module.
- `pytest` is the testing module.
- `-v` enables verbose test output.

Expected result:

`61 passed`

## Quality checks

Routine formatting, linting, and testing can be run together:

```powershell
uv run ruff format .
uv run ruff check .
uv run python -m pytest -v
```

Command explanation:

- `ruff format` applies Ruff's formatting rules.
- `ruff check` runs Ruff's lint and code-quality checks.
- `python -m pytest` runs the test suite through Python.
- Each `.` represents the current directory and its applicable files.
- Each line is a separate PowerShell command and runs sequentially.

Expected results:

- Ruff completes formatting successfully.
- Ruff reports `All checks passed!`
- pytest reports `61 passed`

## Completed checkpoints

### Day 1

- Created the Python project
- Configured uv, pytest, Ruff, Cursor, and GitHub
- Added the initial package and test structure

### Day 2

- Created the `Market` dataclass
- Added market calculations and validation
- Added market unit tests

### Day 3

- Added typed application settings
- Added `.env` configuration
- Protected `.env` from Git
- Added human-readable development logs
- Added JSON production logs
- Updated `main.py` to use structured logging
- Added configuration and logging tests
- Verified all tests, linting, and formatting
- Committed and pushed the completed work to `origin/main`

### Day 4

- Migrated market prices from integer cents to `Decimal` dollar values
- Updated the market model, application, and tests for decimal prices
- Added Pydantic as a direct dependency
- Added typed models for Kalshi market responses
- Included YES and NO bid-and-ask dollar fields
- Added the typed `GetMarketsResponse` pagination model
- Created the asynchronous, read-only `KalshiClient`
- Added limit and cursor query-parameter support
- Added HTTP status-error handling
- Added mocked API-model and API-client tests
- Verified all 21 tests
- Verified Ruff formatting and linting
- Committed and pushed the completed work to `origin/main`

### Day 5

- Added Cryptography as a direct dependency
- Added RSA private-key loading
- Added RSA-PSS and SHA-256 request signing
- Added the required Kalshi authentication-header builder
- Added typed API credential settings
- Added safe credential placeholders to `.env.example`
- Configured a read-only Kalshi demo API key
- Added the typed `GetBalanceResponse` model
- Extended `KalshiClient` with authenticated balance retrieval
- Kept public market requests independent of credentials
- Connected `main.py` to the Kalshi demo environment
- Corrected spelling and validation-message errors
- Verified a live authenticated read-only request returned `HTTP/1.1 200 OK`
- Verified all 26 tests
- Verified Ruff formatting and linting

### Day 6

- Added typed fixed-point order-book response models
- Added authenticated order-book retrieval with depth validation
- Added typed trade-history response models
- Added public trade-history retrieval with pagination and limit validation
- Added typed market-level and event-level position models
- Added authenticated position retrieval with filters, pagination, and limit validation
- Verified that optional query parameters are omitted when unset
- Verified that authenticated signatures exclude query parameters
- Corrected asynchronous test-helper indentation so all assertions execute
- Expanded `main.py` to retrieve markets, an order book, trades, balance, and positions
- Limited live verification to one market, five trades, and ten positions
- Verified all five live read-only API requests returned `HTTP/1.1 200 OK`
- Confirmed that no orders were placed
- Verified all 43 tests
- Verified Ruff formatting and linting

### Day 7

- Added immutable internal order-book, trade, and market-snapshot models
- Added best YES bid and best YES ask properties
- Added safe spread and midpoint properties for incomplete order books
- Added the pure market-snapshot builder
- Converted Kalshi YES bids into best-price-first internal levels
- Converted Kalshi NO bids into implied YES asks
- Normalized YES asks into best-price-first order
- Filtered recent trades to the snapshot's ticker
- Added a caller-provided observation timestamp for deterministic conversion
- Integrated the strategy-ready snapshot into `main.py`
- Logged snapshot prices, calculated values, level counts, and observation time
- Verified correct handling of a live market with no current liquidity or trades
- Confirmed that all API activity remained read-only and no orders were placed
- Added seven market-data tests
- Verified all 50 tests
- Verified Ruff formatting and linting

### Day 8

- Added immutable `QuoteProposal` and `QuoteDecision` strategy-output models
- Added controlled decision reasons for two-sided and incomplete books
- Added the derived `should_quote` property
- Added the pure, deterministic `decide_quotes()` function
- Required quote quantity as an explicit keyword-only argument
- Proposed YES bid and ask quotes at the snapshot's current best prices
- Refused to produce a one-sided quote when either order-book side is missing
- Kept quote proposals independent of Kalshi API order models
- Integrated the quote decision into `main.py` for logging only
- Logged decision reasons, proposed prices, proposed quantities, and quote status
- Verified a live incomplete book produced a safe no-quote decision
- Confirmed that the strategy performed no external action and placed no orders
- Added four quote-strategy tests
- Verified all 54 tests
- Verified Ruff formatting and linting

### Day 9

- Added immutable `RiskDecision` output models
- Added controlled reasons for approval, incomplete quotes, and oversized quotes
- Added the derived `approved` property
- Added the pure, deterministic `evaluate_quote_risk()` function
- Required the maximum quote quantity as an explicit keyword-only argument
- Rejected zero and negative maximum quote quantities
- Rejected decisions missing either the YES bid or YES ask proposal
- Rejected either quote side when its quantity exceeded the configured maximum
- Confirmed that the maximum quote quantity is an inclusive limit
- Added defense-in-depth validation independent of the strategy layer
- Integrated the risk decision into `main.py` for logging only
- Kept strategy quote quantity separate from the risk-layer maximum quantity
- Logged approval status, risk reason, ticker, and maximum quote quantity
- Verified a live incomplete quote produced `approved=False`
- Confirmed that the risk gate performed no external action and placed no orders
- Added seven quote-risk tests
- Verified all 61 tests
- Verified Ruff formatting and linting

## User preferences

- Explain Python concepts in relation to C# where useful
- Explain every PowerShell command, argument, operator, and symbol
- The user manually types all code
- Work incrementally rather than generating the entire bot at once
- Bundle routine formatting, linting, and testing commands when possible
- Use separate checkpoints when a result determines the next implementation step
- Do not begin order placement until the underlying foundation is complete and tested

## Next section

Day 10: add the first dry-run execution-planning boundary while keeping the bot
read-only.

The next work should convert only an approved quote decision into immutable,
Kalshi-independent order intentions for observation and testing. Rejected risk
decisions must produce no order intentions. The new layer should remain pure,
perform no API requests, and submit no orders.

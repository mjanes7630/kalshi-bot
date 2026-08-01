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
- Retrieves the demo portfolio balance
- Retrieves up to ten portfolio positions
- Logs successful and failed demo API-data requests
- Catches expected application, key-loading, and HTTP exceptions
- Uses structured logging instead of `print()`

A live read-only verification returned `HTTP/1.1 200 OK` for markets, the
selected market's order book, trades, balance, and positions. This confirmed
that settings loading, private-key loading, request signing, authentication
headers, public requests, and typed response parsing work together. The live
verification did not place any orders.

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
- `demo_api_data_retrieval_failed`

## Testing

The test suite currently has 43 passing tests:

- 11 market-model tests
- 4 configuration tests
- 3 logging tests
- 5 API-model tests
- 17 API-client tests
- 3 authentication tests

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

`43 passed`

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
- pytest reports `43 passed`

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

## User preferences

- Explain Python concepts in relation to C# where useful
- Explain every PowerShell command, argument, operator, and symbol
- The user manually types all code
- Work incrementally rather than generating the entire bot at once
- Bundle routine formatting, linting, and testing commands when possible
- Use separate checkpoints when a result determines the next implementation step
- Do not begin order placement until the underlying foundation is complete and tested

## Next section

Day 7: build the internal market-data layer that will supply clean,
strategy-ready snapshots.

The next work should convert typed Kalshi market, order-book, and trade responses
into an internal representation that future strategy code can consume without
depending directly on API response models. Continue using the demo environment,
mocked unit tests, and read-only requests. Do not implement order placement yet.

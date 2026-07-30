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

`kalshi_bot/api/models.py` contains typed Pydantic models for Kalshi market
and portfolio responses.

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

`GetBalanceResponse` currently includes:

- `balance`
- `balance_dollars`
- `portfolio_value`
- `updated_ts`

Pydantic converts Kalshi’s fixed-point dollar strings into `Decimal` values.
Unknown response fields are ignored so Kalshi can return additional fields
without breaking the client.

### API client

`kalshi_bot/api/client.py` contains the asynchronous, read-only
`KalshiClient`.

Current behavior:

- Accepts an injected `httpx.AsyncClient`
- Targets Kalshi’s demo REST environment
- Sends a public `GET /markets` request
- Supports the `limit` parameter
- Supports an optional pagination `cursor`
- Accepts optional API-key and RSA private-key credentials
- Sends an authenticated `GET /portfolio/balance` request
- Generates the required millisecond Unix timestamp
- Raises `ValueError` when a protected request is attempted without credentials
- Raises `httpx.HTTPStatusError` for unsuccessful responses
- Validates successful JSON responses through typed Pydantic models
- Does not place orders

The injected HTTP client keeps the API boundary testable with mocked requests.
Public market requests do not require credentials.

### Application

`main.py`:

- Loads typed settings
- Configures structured logging
- Creates a sample market with `Decimal` prices
- Calculates its spread, midpoint, and average trade price
- Classifies trades as below, at, or above the midpoint
- Loads the configured demo RSA private key
- Creates an authenticated `KalshiClient`
- Retrieves the portfolio balance from the Kalshi demo environment
- Logs successful and failed demo balance requests
- Catches expected application, key-loading, and HTTP exceptions
- Uses structured logging instead of `print()`

A live read-only request to the Kalshi demo balance endpoint returned
`HTTP/1.1 200 OK`, confirming that settings loading, private-key loading,
request signing, authentication headers, and response parsing work together.

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
- `demo_balance_retrieved`
- `demo_balance_retrieval_failed`

## Testing

The test suite currently has 26 passing tests:

- 11 market-model tests
- 4 configuration tests
- 3 logging tests
- 2 API-model tests
- 3 API-client tests
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
- Fixed-point API price parsing
- Nested market-response parsing
- Pagination cursor parsing
- Public market request method, path, and query parameters
- Unsuccessful HTTP response handling
- RSA private-key loading from a file
- RSA-PSS and SHA-256 request signing
- Query-parameter removal before signing
- Required Kalshi authentication headers
- Authenticated balance requests
- Cryptographic verification of generated request signatures
- Typed balance-response parsing
- Mocked API requests without live network access

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

`26 passed`

## Quality checks

Routine formatting, linting, and testing can be run together:

```powershell
uv run ruff format .
uv run ruff check .
uv run python -m pytest -v
```

Command explanation:

- `ruff format` applies Ruff’s formatting rules.
- `ruff check` runs Ruff’s lint and code-quality checks.
- `python -m pytest` runs the test suite through Python.
- Each `.` represents the current directory and its applicable files.
- Each line is a separate PowerShell command and runs sequentially.

Expected results:

- Ruff completes formatting successfully.
- Ruff reports `All checks passed!`
- pytest reports `26 passed`

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

## User preferences

- Explain Python concepts in relation to C# where useful
- Explain every PowerShell command, argument, operator, and symbol
- The user manually types all code
- Work incrementally rather than generating the entire bot at once
- Bundle routine formatting, linting, and testing commands when possible
- Use separate checkpoints when a result determines the next implementation step
- Do not begin order placement until the underlying foundation is complete and tested

## Next section

Day 6: expand the typed, read-only Kalshi REST API coverage.

The next work should add the REST data needed by the future strategy through
small, tested client methods. Continue using the demo environment and mocked
unit tests. Do not implement order placement or the market-making loop yet.

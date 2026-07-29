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
- GitHub repository configured
- Cursor launch configuration runs `kalshi_bot.main` as a module

## Project structure

- `kalshi_bot/api/__init__.py`
- `kalshi_bot/api/client.py`
- `kalshi_bot/api/models.py`
- `kalshi_bot/config.py`
- `kalshi_bot/logging_config.py`
- `kalshi_bot/main.py`
- `kalshi_bot/models/market.py`
- `tests/test_api_client.py`
- `tests/test_api_models.py`
- `tests/test_config.py`
- `tests/test_logging_config.py`
- `tests/test_market.py`
- `.vscode/launch.json`
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

### API response models

`kalshi_bot/api/models.py` contains typed Pydantic models for Kalshi’s
`GET /markets` response.

`KalshiMarket` currently includes:

- `ticker`
- `title`
- `yes_bid_dollars`
- `yes_ask_dollars`
- `no_bid_dollars`
- `no_ask_dollars`
- `last_price_dollars`

Pydantic converts Kalshi’s fixed-point price strings into `Decimal` values.

Unknown response fields are ignored so Kalshi can return additional fields
without breaking the initial client.

`GetMarketsResponse` contains:

- A list of `KalshiMarket` objects
- The pagination cursor

### API client

`kalshi_bot/api/client.py` contains the initial asynchronous `KalshiClient`.

Current behavior:

- Accepts an injected `httpx.AsyncClient`
- Sends a read-only `GET /markets` request
- Supports the `limit` parameter
- Supports an optional pagination `cursor`
- Raises `httpx.HTTPStatusError` for unsuccessful responses
- Validates successful JSON responses through `GetMarketsResponse`
- Does not place orders
- Does not contain authentication or request-signing behavior yet

The injected HTTP client keeps the API boundary testable without contacting
the live Kalshi service.

### Application

`main.py`:

- Loads typed settings
- Configures structured logging
- Creates a sample market
- Calculates its spread, midpoint, and average trade price
- Classifies trades as below, at, or above the midpoint
- Catches expected `TypeError` and `ValueError` exceptions
- Uses structured logging instead of `print()`

### Configuration

`config.py` provides a typed `Settings` class.

Current settings include:

- `environment`
- `log_level`

Configuration behavior:

- Uses safe defaults when values are not provided
- Loads local values from `.env`
- Supports `KALSHI_BOT_` environment-variable overrides
- Allows `development` and `production` environments
- Rejects invalid environment values
- `.env` is excluded from Git through `.gitignore`

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

## Testing

The test suite currently has 21 passing tests:

- 11 market-model tests
- 3 configuration tests
- 3 logging tests
- 2 API-model tests
- 2 API-client tests

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
- Invalid environment rejection
- Development console logging
- Production JSON logging
- Log-level filtering
- Fixed-point API price parsing
- Nested market-response parsing
- Pagination cursor parsing
- HTTP method, path, and query parameters
- Unsuccessful HTTP response handling
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

`21 passed`

## Quality checks

Routine formatting, linting, and testing can be run together:

```powershell
uv run ruff format .
uv run ruff check .
uv run python -m pytest -v
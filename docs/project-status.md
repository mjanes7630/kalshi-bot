# Kalshi Bot Project Status

## Environment

- Windows
- Cursor
- Python 3.14
- uv for dependency management
- pytest for testing
- GitHub repository configured
- Cursor launch configuration runs `kalshi_bot.main` as a module

## Project structure

- `kalshi_bot/main.py`
- `kalshi_bot/models/market.py`
- `tests/test_market.py`
- `.vscode/launch.json`
- `pyproject.toml`
- `uv.lock`

## Current implementation

`Market` is a dataclass containing:

- ticker
- title
- best_bid
- best_ask
- recent_trade_prices

It provides methods for:

- spread calculation
- midpoint calculation
- average trade-price calculation

Validation runs through `__post_init__`.

Prices:

- Must be integers
- Cannot be Boolean values
- Must be between 0 and 100
- Best bid cannot exceed best ask
- Empty trade lists are allowed, but calculating their average raises `ValueError`

`main.py` catches expected `TypeError` and `ValueError` exceptions.

## Testing

pytest is installed as a development dependency.

The test suite currently has 10 passing test cases covering:

- Spread
- Midpoint
- Average trade price
- Crossed markets
- Incorrect price types
- Empty trade-list averages
- Prices outside the valid range
- Parameterized validation cases with readable IDs

Run tests with:

`uv run python -m pytest -v`

## User preferences

- Explain Python concepts in relation to C# where useful.
- Explain every PowerShell command and symbol.
- User manually types all code.
- Work incrementally rather than generating the entire bot at once.

## Next section

Day 3: configuration, environment variables, and structured logging.
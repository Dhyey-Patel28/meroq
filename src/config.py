from __future__ import annotations

DEFAULT_WATCHLIST = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "JPM",
    "SPY",
]

SUGGESTED_PERIODS = ["1y", "2y", "5y", "10y", "max"]
SUGGESTED_INTERVALS = ["1d", "1wk"]

# Rough defaults for walk-forward testing. These values keep the app responsive
# while still testing across multiple future windows.
WALK_FORWARD_DEFAULTS = {
    "1d": {
        "initial_train_size": 756,  # roughly 3 trading years
        "test_size": 21,            # roughly 1 trading month
        "step_size": 21,
        "periods_per_year": 252,
    },
    "1wk": {
        "initial_train_size": 156,  # roughly 3 years
        "test_size": 4,             # roughly 1 month
        "step_size": 4,
        "periods_per_year": 52,
    },
}

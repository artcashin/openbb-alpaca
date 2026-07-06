"""Shared fixtures for openbb-alpaca tests."""


import pytest


# ---------------------------------------------------------------------------
# Sample Alpaca API responses (as returned by aextract_data)
# ---------------------------------------------------------------------------

@pytest.fixture
def equity_bars():
    """Simulated Alpaca equity bars response for a single symbol."""
    return [
        {"t": "2026-01-02T09:30:00Z", "o": 150.0, "h": 153.0, "l": 149.0,
         "c": 152.0, "v": 1000, "vw": 151.2, "n": 50, "symbol": "AAPL"},
        {"t": "2026-01-02T09:31:00Z", "o": 152.0, "h": 154.0, "l": 151.0,
         "c": 153.0, "v": 1100, "vw": 152.5, "n": 60, "symbol": "AAPL"},
    ]


@pytest.fixture
def equity_daily_bars():
    """Daily bars (date-only timestamps)."""
    return [
        {"t": "2026-01-02", "o": 150.0, "h": 153.0, "l": 149.0,
         "c": 152.0, "v": 10000, "vw": 151.2, "n": 500, "symbol": "AAPL"},
        {"t": "2026-01-03", "o": 152.0, "h": 154.0, "l": 151.0,
         "c": 153.0, "v": 11000, "vw": 152.5, "n": 600, "symbol": "AAPL"},
    ]


@pytest.fixture
def crypto_bars():
    """Simulated Alpaca crypto bars (UTC timestamps)."""
    return [
        {"t": "2026-01-02T00:00:00Z", "o": 50000.0, "h": 51000.0, "l": 49000.0,
         "c": 50500.0, "v": 100.5, "vw": 50200.0, "n": 5000, "symbol": "BTC/USD"},
        {"t": "2026-01-02T01:00:00Z", "o": 50500.0, "h": 51500.0, "l": 50000.0,
         "c": 51000.0, "v": 150.2, "vw": 50700.0, "n": 6000, "symbol": "BTC/USD"},
    ]


@pytest.fixture
def crypto_daily_bars():
    """Daily crypto bars."""
    return [
        {"t": "2026-01-02", "o": 50000.0, "h": 52000.0, "l": 48000.0,
         "c": 51000.0, "v": 1000.5, "vw": 50500.0, "n": 50000, "symbol": "BTC/USD"},
    ]


@pytest.fixture
def multi_symbol_bars():
    """Bars from two symbols for multi-symbol query testing."""
    return [
        {"t": "2026-01-02T09:30:00Z", "o": 150.0, "h": 153.0, "l": 149.0,
         "c": 152.0, "v": 1000, "vw": 151.2, "n": 50, "symbol": "AAPL"},
        {"t": "2026-01-02T09:30:00Z", "o": 300.0, "h": 305.0, "l": 298.0,
         "c": 302.0, "v": 2000, "vw": 301.5, "n": 80, "symbol": "MSFT"},
    ]


@pytest.fixture
def bars_without_timestamp():
    """Bar missing the 't' key (should be skipped by transform_data)."""
    return [
        {"o": 150.0, "h": 153.0, "l": 149.0, "c": 152.0, "v": 1000,
         "symbol": "AAPL"},
    ]


# ---------------------------------------------------------------------------
# Mock API response for paginate_bars
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_paginated_response():
    """Returns a function that simulates a multi-page Alpaca response."""

    page1 = {
        "bars": {
            "AAPL": [
                {"t": "2026-01-02T09:30:00Z", "o": 150.0, "h": 153.0,
                 "l": 149.0, "c": 152.0, "v": 1000, "vw": 151.2, "n": 50},
            ]
        },
        "next_page_token": "token2",
    }
    page2 = {
        "bars": {
            "AAPL": [
                {"t": "2026-01-02T09:31:00Z", "o": 152.0, "h": 154.0,
                 "l": 151.0, "c": 153.0, "v": 1100, "vw": 152.5, "n": 60},
            ]
        },
        "next_page_token": None,
    }
    call_count = 0

    async def mock_request(url, method, headers, params, timeout):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return page1
        return page2

    return mock_request


@pytest.fixture
def mock_single_page_response():
    """Returns a function that simulates a single-page Alpaca response."""
    async def mock_request(url, method, headers, params, timeout):
        return {
            "bars": {
                "AAPL": [
                    {"t": "2026-01-02T09:30:00Z", "o": 150.0, "h": 153.0,
                     "l": 149.0, "c": 152.0, "v": 1000, "vw": 151.2, "n": 50},
                ]
            },
            "next_page_token": None,
        }

    return mock_request

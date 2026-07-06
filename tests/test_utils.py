"""Tests for openbb_alpaca.utils."""

import asyncio
from unittest.mock import patch

import pytest

from openbb_alpaca.utils import (
    ALPACA_MAX_PER_PAGE,
    DAILY_OR_LONGER,
    INTERVAL_MAP,
    paginate_bars,
)


# ============================================================
# Constants
# ============================================================

class TestConstants:
    def test_interval_map_has_all_keys(self):
        assert set(INTERVAL_MAP) == {"1m", "5m", "15m", "30m", "1h", "1d", "1W", "1M"}

    def test_daily_or_longer(self):
        assert "1d" in DAILY_OR_LONGER
        assert "1W" in DAILY_OR_LONGER
        assert "1M" in DAILY_OR_LONGER
        assert "1h" not in DAILY_OR_LONGER

    def test_max_per_page(self):
        assert ALPACA_MAX_PER_PAGE == 10000


# ============================================================
# paginate_bars  (async — run via asyncio.run)
# ============================================================

def _run(async_fn, *args, **kwargs):
    """Run an async function synchronously."""
    return asyncio.run(async_fn(*args, **kwargs))


class TestPaginateBars:
    PATCH_TARGET = "openbb_core.provider.utils.helpers.amake_request"

    def test_single_page(self, mock_single_page_response):
        async def go():
            with patch(self.PATCH_TARGET, mock_single_page_response):
                return await paginate_bars(
                    "https://example.com", {"auth": "token"}, {"symbols": "AAPL"}
                )
        results = _run(go)
        assert len(results) == 1
        assert results[0]["symbol"] == "AAPL"
        assert results[0]["o"] == 150.0

    def test_multi_page(self, mock_paginated_response):
        async def go():
            with patch(self.PATCH_TARGET, mock_paginated_response):
                return await paginate_bars(
                    "https://example.com", {"auth": "token"}, {"symbols": "AAPL"}
                )
        results = _run(go)
        assert len(results) == 2
        for r in results:
            assert r["symbol"] == "AAPL"

    def test_empty_response_raises(self):
        async def empty_response(url, method, headers, params, timeout):
            return {"bars": {}, "next_page_token": None}

        async def go():
            with patch(self.PATCH_TARGET, empty_response):
                return await paginate_bars(
                    "https://example.com", {}, {"symbols": "AAPL"}
                )
        with pytest.raises(Exception, match="The request was returned empty"):
            _run(go)

    def test_custom_empty_message(self):
        async def empty_response(url, method, headers, params, timeout):
            return {"bars": {}, "next_page_token": None}

        async def go():
            with patch(self.PATCH_TARGET, empty_response):
                return await paginate_bars(
                    "https://example.com", {}, {"symbols": "AAPL"},
                    empty_message="custom message",
                )
        with pytest.raises(Exception, match="custom message"):
            _run(go)

    def test_error_response_with_message(self):
        async def error_response(url, method, headers, params, timeout):
            return {"message": "Invalid API key"}

        from openbb_core.provider.utils.errors import UnauthorizedError

        async def go():
            with patch(self.PATCH_TARGET, error_response):
                return await paginate_bars(
                    "https://example.com", {}, {"symbols": "AAPL"}
                )
        with pytest.raises(UnauthorizedError, match="Invalid API key"):
            _run(go)

    def test_non_dict_response(self):
        async def bad_response(url, method, headers, params, timeout):
            return "not a dict"

        from openbb_core.provider.utils.errors import EmptyDataError

        async def go():
            with patch(self.PATCH_TARGET, bad_response):
                return await paginate_bars(
                    "https://example.com", {}, {"symbols": "AAPL"}
                )
        with pytest.raises(EmptyDataError, match="Unexpected response"):
            _run(go)

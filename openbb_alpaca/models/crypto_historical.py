"""Alpaca Crypto Historical Price Model."""

# pylint: disable=unused-argument

from datetime import datetime
from typing import Any, Literal

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.crypto_historical import (
    CryptoHistoricalData,
    CryptoHistoricalQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError
from pydantic import Field

from openbb_alpaca.models.equity_historical import DAILY_OR_LONGER, INTERVAL_MAP

# Alpaca crypto market data is a separate (free) endpoint; no feed/adjustment.
BASE_URL = "https://data.alpaca.markets/v1beta3/crypto/us/bars"
_QUOTES = ["USDT", "USDC", "USD", "BTC", "ETH", "EUR", "DAI"]


def _normalize_symbol(sym: str) -> str:
    """Coerce a symbol to Alpaca's 'BASE/QUOTE' form (e.g. BTC-USD -> BTC/USD)."""
    s = sym.strip().upper()
    if "/" in s:
        return s
    if "-" in s:
        return s.replace("-", "/")
    for q in _QUOTES:
        if s.endswith(q) and len(s) > len(q):
            return f"{s[:-len(q)]}/{q}"
    return s


class AlpacaCryptoHistoricalQueryParams(CryptoHistoricalQueryParams):
    """Alpaca Crypto Historical Price Query.

    Source: https://docs.alpaca.markets/reference/cryptobars
    """

    __json_schema_extra__ = {
        "symbol": {"multiple_items_allowed": True},
        "interval": {"choices": list(INTERVAL_MAP)},
    }

    interval: Literal["1m", "5m", "15m", "30m", "1h", "1d", "1W", "1M"] = Field(
        default="1d", description=QUERY_DESCRIPTIONS.get("interval", "")
    )


class AlpacaCryptoHistoricalData(CryptoHistoricalData):
    """Alpaca Crypto Historical Price Data."""

    vwap: float | None = Field(
        default=None, description="Volume-weighted average price for the bar."
    )
    transactions: int | None = Field(
        default=None, description="Number of trades in the bar."
    )


class AlpacaCryptoHistoricalFetcher(
    Fetcher[
        AlpacaCryptoHistoricalQueryParams,
        list[AlpacaCryptoHistoricalData],
    ]
):
    """Transform the query, extract and transform the data from Alpaca crypto bars."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AlpacaCryptoHistoricalQueryParams:
        """Transform the query params; default to a 1-year window."""
        # pylint: disable=import-outside-toplevel
        from dateutil.relativedelta import relativedelta

        transformed = dict(params)
        now = datetime.now().date()
        if transformed.get("start_date") is None:
            transformed["start_date"] = now - relativedelta(years=1)
        if transformed.get("end_date") is None:
            transformed["end_date"] = now
        return AlpacaCryptoHistoricalQueryParams(**transformed)

    @staticmethod
    async def aextract_data(
        query: AlpacaCryptoHistoricalQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw bars from the Alpaca crypto endpoint."""
        # pylint: disable=import-outside-toplevel
        from openbb_core.provider.utils.helpers import amake_request

        api_key = (credentials or {}).get("alpaca_api_key")
        api_secret = (credentials or {}).get("alpaca_api_secret")
        if not api_key or not api_secret:
            raise UnauthorizedError(
                "Missing Alpaca credentials. Set ALPACA_API_KEY and ALPACA_API_SECRET."
            )

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "accept": "application/json",
        }
        symbols = ",".join(_normalize_symbol(s) for s in query.symbol.split(","))
        base_params: dict[str, Any] = {
            "symbols": symbols,
            "timeframe": INTERVAL_MAP[query.interval],
            "start": str(query.start_date),
            "end": str(query.end_date),
            "limit": 10000,
            "sort": "asc",
        }

        results: list[dict] = []
        page_token: str | None = None
        while True:
            params = dict(base_params)
            if page_token:
                params["page_token"] = page_token
            response = await amake_request(
                BASE_URL, method="GET", headers=headers, params=params, timeout=30
            )
            if not isinstance(response, dict):
                raise EmptyDataError("Unexpected response from Alpaca.")
            if response.get("message") and not response.get("bars"):
                raise UnauthorizedError(f"Alpaca: {response['message']}")

            for sym, bars in (response.get("bars") or {}).items():
                for bar in bars or []:
                    bar["symbol"] = sym
                    results.append(bar)

            page_token = response.get("next_page_token")
            if not page_token:
                break

        if not results:
            raise EmptyDataError("The request was returned empty.")
        return results

    @staticmethod
    def transform_data(
        query: AlpacaCryptoHistoricalQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[AlpacaCryptoHistoricalData]:
        """Map Alpaca crypto bar fields to the standard model (timestamps in UTC)."""
        # pylint: disable=import-outside-toplevel
        from pandas import to_datetime

        multiple = "," in query.symbol
        results: list[AlpacaCryptoHistoricalData] = []
        for bar in data:
            if query.interval in DAILY_OR_LONGER:
                bar_date: Any = to_datetime(bar["t"]).date()
            else:
                bar_date = to_datetime(bar["t"], utc=True)  # crypto trades 24/7 UTC
            item = {
                "date": bar_date,
                "open": bar.get("o"),
                "high": bar.get("h"),
                "low": bar.get("l"),
                "close": bar.get("c"),
                "volume": bar.get("v"),
                "vwap": bar.get("vw"),
                "transactions": bar.get("n"),
            }
            if multiple:
                item["symbol"] = bar.get("symbol")
            results.append(AlpacaCryptoHistoricalData.model_validate(item))
        results.sort(key=lambda r: (str(getattr(r, "symbol", "")), r.date))
        return results

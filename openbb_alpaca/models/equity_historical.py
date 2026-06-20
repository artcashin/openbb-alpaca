"""Alpaca Equity Historical Price Model."""

# pylint: disable=unused-argument

from datetime import datetime
from typing import Any, Literal

from openbb_core.provider.abstract.fetcher import Fetcher
from openbb_core.provider.standard_models.equity_historical import (
    EquityHistoricalData,
    EquityHistoricalQueryParams,
)
from openbb_core.provider.utils.descriptions import QUERY_DESCRIPTIONS
from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError
from pydantic import Field

# OpenBB interval -> Alpaca timeframe string.
INTERVAL_MAP = {
    "1m": "1Min",
    "5m": "5Min",
    "15m": "15Min",
    "30m": "30Min",
    "1h": "1Hour",
    "1d": "1Day",
    "1W": "1Week",
    "1M": "1Month",
}
DAILY_OR_LONGER = {"1d", "1W", "1M"}
BASE_URL = "https://data.alpaca.markets/v2/stocks/bars"


class AlpacaEquityHistoricalQueryParams(EquityHistoricalQueryParams):
    """Alpaca Equity Historical Price Query.

    Source: https://docs.alpaca.markets/reference/stockbars
    """

    __json_schema_extra__ = {
        "symbol": {"multiple_items_allowed": True},
        "interval": {"choices": list(INTERVAL_MAP)},
        "feed": {"choices": ["iex", "sip", "otc"]},
        "adjustment": {"choices": ["raw", "splits", "dividends", "all"]},
    }

    interval: Literal["1m", "5m", "15m", "30m", "1h", "1d", "1W", "1M"] = Field(
        default="1d", description=QUERY_DESCRIPTIONS.get("interval", "")
    )
    feed: Literal["iex", "sip", "otc"] = Field(
        default="iex",
        description="The source feed of the data. 'iex' is free; 'sip' requires a"
        " paid Alpaca market-data subscription.",
    )
    adjustment: Literal["raw", "splits", "dividends", "all"] = Field(
        default="splits",
        description="The corporate-action adjustment applied to the prices.",
    )


class AlpacaEquityHistoricalData(EquityHistoricalData):
    """Alpaca Equity Historical Price Data."""

    vwap: float | None = Field(
        default=None, description="Volume-weighted average price for the bar."
    )
    transactions: int | None = Field(
        default=None,
        description="Number of trades in the bar.",
    )


class AlpacaEquityHistoricalFetcher(
    Fetcher[
        AlpacaEquityHistoricalQueryParams,
        list[AlpacaEquityHistoricalData],
    ]
):
    """Transform the query, extract and transform the data from Alpaca endpoints."""

    @staticmethod
    def transform_query(params: dict[str, Any]) -> AlpacaEquityHistoricalQueryParams:
        """Transform the query params; default to a 1-year window."""
        # pylint: disable=import-outside-toplevel
        from dateutil.relativedelta import relativedelta

        transformed = dict(params)
        now = datetime.now().date()
        if transformed.get("start_date") is None:
            transformed["start_date"] = now - relativedelta(years=1)
        if transformed.get("end_date") is None:
            transformed["end_date"] = now
        return AlpacaEquityHistoricalQueryParams(**transformed)

    @staticmethod
    async def aextract_data(
        query: AlpacaEquityHistoricalQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw bars from the Alpaca market-data endpoint."""
        # pylint: disable=import-outside-toplevel
        from openbb_core.provider.utils.helpers import amake_request

        api_key = (credentials or {}).get("alpaca_api_key")
        api_secret = (credentials or {}).get("alpaca_api_secret")
        if not api_key or not api_secret:
            raise UnauthorizedError(
                "Missing Alpaca credentials. Set ALPACA_API_KEY and"
                " ALPACA_API_SECRET."
            )

        headers = {
            "APCA-API-KEY-ID": api_key,
            "APCA-API-SECRET-KEY": api_secret,
            "accept": "application/json",
        }
        symbols = ",".join(s.strip().upper() for s in query.symbol.split(","))
        base_params: dict[str, Any] = {
            "symbols": symbols,
            "timeframe": INTERVAL_MAP[query.interval],
            "start": str(query.start_date),
            "end": str(query.end_date),
            "adjustment": query.adjustment,
            "feed": query.feed,
            "limit": 10000,
            "sort": "asc",
        }

        results: list[dict] = []
        page_token: str | None = None
        # Alpaca paginates via next_page_token; loop until exhausted.
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
        query: AlpacaEquityHistoricalQueryParams,
        data: list[dict],
        **kwargs: Any,
    ) -> list[AlpacaEquityHistoricalData]:
        """Map Alpaca bar fields to the standard model."""
        # pylint: disable=import-outside-toplevel
        from pandas import to_datetime
        from pytz import timezone

        multiple = "," in query.symbol
        results: list[AlpacaEquityHistoricalData] = []
        for bar in data:
            if query.interval in DAILY_OR_LONGER:
                bar_date: Any = to_datetime(bar["t"]).date()
            else:
                bar_date = to_datetime(bar["t"], utc=True).tz_convert(
                    timezone("America/New_York")
                )
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
            results.append(AlpacaEquityHistoricalData.model_validate(item))
        # Chronological, then by symbol when multiple.
        results.sort(key=lambda r: (str(getattr(r, "symbol", "")), r.date))
        return results

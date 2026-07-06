"""Alpaca Crypto Historical Price Model."""

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

from openbb_alpaca.utils import (
    ALPACA_MAX_PER_PAGE,
    DAILY_OR_LONGER,
    INTERVAL_MAP,
    paginate_bars,
)

# Alpaca crypto market data is a separate (free) endpoint;
# it only supports USD-quoted pairs (e.g. BTC/USD, not BTC/EUR).
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

    # OpenBB core reads this dunder directly (registry_map / package_builder) for
    # multi-symbol + choices; pydantic's model_config json_schema_extra is a
    # different mechanism core never inspects, so it must stay this attribute.
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
    # pylint: disable=unused-argument
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
    # pylint: disable=unused-argument
    async def aextract_data(
        query: AlpacaCryptoHistoricalQueryParams,
        credentials: dict[str, str] | None,
        **kwargs: Any,
    ) -> list[dict]:
        """Return the raw bars from the Alpaca crypto endpoint."""
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
        raw_symbols = [
            _normalize_symbol(s) for s in query.symbol.split(",") if s.strip()
        ]
        if not raw_symbols:
            raise EmptyDataError("No symbols provided.")
        symbols = ",".join(raw_symbols)

        base_params: dict[str, Any] = {
            "symbols": symbols,
            "timeframe": INTERVAL_MAP[query.interval],
            "start": str(query.start_date),
            "end": str(query.end_date),
            "limit": ALPACA_MAX_PER_PAGE,
            "sort": "asc",
        }

        return await paginate_bars(
            BASE_URL,
            headers,
            base_params,
            empty_message=(
                "Alpaca crypto endpoint only supports USD-quoted pairs "
                "(e.g. BTC/USD, ETH/USD)."
            ),
        )

    @staticmethod
    # pylint: disable=unused-argument
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
            ts = bar.get("t")
            if ts is None:
                continue
            if query.interval in DAILY_OR_LONGER:
                bar_date: Any = to_datetime(ts).date()
            else:
                bar_date = to_datetime(ts, utc=True)
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

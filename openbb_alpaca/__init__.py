"""Alpaca provider module for OpenBB."""

from openbb_core.provider.abstract.provider import Provider

from openbb_alpaca.models.equity_historical import AlpacaEquityHistoricalFetcher

alpaca_provider = Provider(
    name="alpaca",
    website="https://alpaca.markets",
    description=(
        "Alpaca Market Data API. Provides historical equity/ETF pricing (bars) "
        "via the free IEX feed or the paid SIP consolidated feed."
    ),
    # Becomes the credential fields `alpaca_api_key` and `alpaca_api_secret`.
    credentials=["api_key", "api_secret"],
    fetcher_dict={
        "EquityHistorical": AlpacaEquityHistoricalFetcher,
        "EtfHistorical": AlpacaEquityHistoricalFetcher,
    },
    repr_name="Alpaca",
)

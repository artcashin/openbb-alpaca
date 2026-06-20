"""Alpaca provider module for OpenBB."""

from openbb_core.provider.abstract.provider import Provider

from openbb_alpaca.models.crypto_historical import AlpacaCryptoHistoricalFetcher
from openbb_alpaca.models.equity_historical import AlpacaEquityHistoricalFetcher

alpaca_provider = Provider(
    name="alpaca",
    website="https://alpaca.markets",
    description=(
        "Alpaca Market Data API. Provides historical equity/ETF pricing (bars) "
        "via the free IEX feed or the paid SIP consolidated feed, and crypto "
        "pricing via the free crypto market-data endpoint."
    ),
    # Becomes the credential fields `alpaca_api_key` and `alpaca_api_secret`.
    credentials=["api_key", "api_secret"],
    fetcher_dict={
        "EquityHistorical": AlpacaEquityHistoricalFetcher,
        "EtfHistorical": AlpacaEquityHistoricalFetcher,
        "CryptoHistorical": AlpacaCryptoHistoricalFetcher,
    },
    repr_name="Alpaca",
)

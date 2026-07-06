"""Shared helpers and constants for the Alpaca provider."""

from typing import Any

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

# Alpaca's max bars per page; used to minimise round-trips.
ALPACA_MAX_PER_PAGE = 10000


async def paginate_bars(
    base_url: str,
    headers: dict[str, str],
    base_params: dict[str, Any],
    empty_message: str | None = None,
) -> list[dict]:
    """Fetch all pages of Alpaca bars via *next_page_token*.

    Returns a flat list of dicts, each containing a ``"symbol"`` key set to the
    symbol the bar belongs to.
    """
    # pylint: disable=import-outside-toplevel
    from openbb_core.provider.utils.errors import EmptyDataError, UnauthorizedError
    from openbb_core.provider.utils.helpers import amake_request

    results: list[dict] = []
    page_token: str | None = None

    while True:
        params = dict(base_params)
        if page_token:
            params["page_token"] = page_token
        response = await amake_request(
            base_url, method="GET", headers=headers, params=params, timeout=30
        )
        if not isinstance(response, dict):
            raise EmptyDataError(f"Unexpected response from Alpaca: {response!r}")
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
        raise EmptyDataError(empty_message or "The request was returned empty.")
    return results

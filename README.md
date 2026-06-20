# openbb-alpaca

A minimal [Alpaca](https://alpaca.markets) provider extension for the OpenBB
Platform. Adds Alpaca as a source for **equity, ETF, and crypto historical
pricing**:

```python
from openbb import obb
obb.equity.price.historical("AAPL", provider="alpaca", interval="1d")
obb.crypto.price.historical("BTC/USD", provider="alpaca", interval="1h")  # BTC-USD / BTCUSD also accepted
```

## Credentials

Set both (bare UPPERCASE env vars, or via OpenBB user settings):

- `ALPACA_API_KEY`    — Alpaca API key id
- `ALPACA_API_SECRET` — Alpaca API secret key

A free Alpaca account works with the default **IEX** feed. The consolidated
**SIP** feed requires a paid Alpaca market-data subscription (pass `feed="sip"`).

## Supported

- `EquityHistorical` / `EtfHistorical` — historical bars
  (intervals: `1m, 5m, 15m, 30m, 1h, 1d, 1W, 1M`; feeds: `iex` (default), `sip`,
  `otc`; adjustments: `raw, splits` (default), `dividends, all`).
- `CryptoHistorical` — historical bars from Alpaca's free crypto endpoint
  (same intervals; no feed/adjustment). Symbols accept `BTC/USD`, `BTC-USD`, or
  `BTCUSD`; timestamps are UTC.

Asset classes Alpaca does not provide market data for (forex, indices, futures)
are intentionally absent. Options bars require a paid subscription and are not
included.

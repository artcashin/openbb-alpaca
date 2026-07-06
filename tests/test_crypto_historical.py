"""Tests for openbb_alpaca.models.crypto_historical."""

from datetime import date, datetime


from openbb_alpaca.models.crypto_historical import (
    AlpacaCryptoHistoricalData,
    AlpacaCryptoHistoricalFetcher,
    AlpacaCryptoHistoricalQueryParams,
    _normalize_symbol,
)


# ============================================================
# _normalize_symbol
# ============================================================

class TestNormalizeSymbol:
    def test_already_normalized(self):
        assert _normalize_symbol("BTC/USD") == "BTC/USD"

    def test_dash_format(self):
        assert _normalize_symbol("BTC-USD") == "BTC/USD"

    def test_suffix_usd(self):
        assert _normalize_symbol("BTCUSD") == "BTC/USD"

    def test_suffix_usdt(self):
        assert _normalize_symbol("ETHUSDT") == "ETH/USDT"

    def test_suffix_btc(self):
        assert _normalize_symbol("ETHBTC") == "ETH/BTC"

    def test_suffix_eth(self):
        assert _normalize_symbol("LINKETH") == "LINK/ETH"

    def test_suffix_eur(self):
        assert _normalize_symbol("BTCEUR") == "BTC/EUR"

    def test_suffix_dai(self):
        assert _normalize_symbol("ETHDAI") == "ETH/DAI"

    def test_lowercase_input(self):
        assert _normalize_symbol("btc-usd") == "BTC/USD"

    def test_whitespace_stripped(self):
        assert _normalize_symbol("  BTC-USD  ") == "BTC/USD"

    def test_unrecognized_passes_through(self):
        assert _normalize_symbol("FOO") == "FOO"

    def test_empty_string(self):
        assert _normalize_symbol("") == ""


# ============================================================
# Query params
# ============================================================

class TestQueryParams:
    def test_default_interval(self):
        params = AlpacaCryptoHistoricalQueryParams(symbol="BTC/USD")
        assert params.interval == "1d"

    def test_custom_interval(self):
        params = AlpacaCryptoHistoricalQueryParams(symbol="BTC/USD", interval="1h")
        assert params.interval == "1h"


# ============================================================
# transform_query
# ============================================================

class TestTransformQuery:
    def test_defaults_set(self):
        qp = AlpacaCryptoHistoricalFetcher.transform_query(
            {"symbol": "BTC/USD"}
        )
        assert qp.start_date is not None
        assert qp.end_date is not None
        assert qp.start_date < qp.end_date

    def test_dates_preserved(self):
        qp = AlpacaCryptoHistoricalFetcher.transform_query(
            {"symbol": "BTC/USD", "start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert str(qp.start_date) == "2026-01-01"
        assert str(qp.end_date) == "2026-01-31"


# ============================================================
# transform_data
# ============================================================

class TestTransformData:
    def test_daily_returns_date(self, crypto_daily_bars):
        qp = AlpacaCryptoHistoricalQueryParams(
            symbol="BTC/USD", interval="1d"
        )
        results = AlpacaCryptoHistoricalFetcher.transform_data(qp, crypto_daily_bars)
        assert len(results) == 1
        r = results[0]
        assert isinstance(r.date, date)
        assert r.open == 50000.0
        assert r.close == 51000.0

    def test_intraday_returns_datetime(self, crypto_bars):
        qp = AlpacaCryptoHistoricalQueryParams(
            symbol="BTC/USD", interval="1h"
        )
        results = AlpacaCryptoHistoricalFetcher.transform_data(qp, crypto_bars)
        assert len(results) == 2
        for r in results:
            assert isinstance(r.date, datetime)

    def test_missing_timestamp_skipped(self, crypto_daily_bars, bars_without_timestamp):
        qp = AlpacaCryptoHistoricalQueryParams(symbol="BTC/USD")
        results = AlpacaCryptoHistoricalFetcher.transform_data(
            qp, crypto_daily_bars + bars_without_timestamp
        )
        assert len(results) == 1

    def test_vwap_and_transactions(self, crypto_bars):
        qp = AlpacaCryptoHistoricalQueryParams(symbol="BTC/USD", interval="1h")
        results = AlpacaCryptoHistoricalFetcher.transform_data(qp, crypto_bars)
        assert results[0].vwap == 50200.0
        assert results[0].transactions == 5000

    def test_sorted_by_date(self, crypto_bars):
        qp = AlpacaCryptoHistoricalQueryParams(symbol="BTC/USD", interval="1h")
        results = AlpacaCryptoHistoricalFetcher.transform_data(
            qp, list(reversed(crypto_bars))
        )
        dates = [r.date for r in results]
        assert dates == sorted(dates)


# ============================================================
# Data model
# ============================================================

class TestDataModel:
    def test_creation(self):
        d = AlpacaCryptoHistoricalData.model_validate({
            "date": "2026-01-02", "open": 50000.0, "close": 51000.0,
        })
        assert d.open == 50000.0
        assert d.close == 51000.0

    def test_vwap_optional(self):
        d = AlpacaCryptoHistoricalData.model_validate({
            "date": "2026-01-02", "open": 50000.0, "close": 51000.0,
        })
        assert d.vwap is None

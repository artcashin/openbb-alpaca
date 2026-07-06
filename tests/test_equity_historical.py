"""Tests for openbb_alpaca.models.equity_historical."""

from datetime import date, datetime


from openbb_alpaca.models.equity_historical import (
    AlpacaEquityHistoricalData,
    AlpacaEquityHistoricalFetcher,
    AlpacaEquityHistoricalQueryParams,
)


# ============================================================
# Query params
# ============================================================

class TestQueryParams:
    def test_default_interval(self):
        params = AlpacaEquityHistoricalQueryParams(symbol="AAPL")
        assert params.interval == "1d"

    def test_default_feed(self):
        params = AlpacaEquityHistoricalQueryParams(symbol="AAPL")
        assert params.feed == "iex"

    def test_default_adjustment(self):
        params = AlpacaEquityHistoricalQueryParams(symbol="AAPL")
        assert params.adjustment == "splits"

    def test_custom_values(self):
        params = AlpacaEquityHistoricalQueryParams(
            symbol="AAPL", interval="1h", feed="sip", adjustment="all"
        )
        assert params.interval == "1h"
        assert params.feed == "sip"
        assert params.adjustment == "all"


# ============================================================
# transform_query
# ============================================================

class TestTransformQuery:
    def test_defaults_set(self):
        qp = AlpacaEquityHistoricalFetcher.transform_query({"symbol": "AAPL"})
        assert qp.start_date is not None
        assert qp.end_date is not None
        assert qp.start_date < qp.end_date

    def test_dates_preserved(self):
        qp = AlpacaEquityHistoricalFetcher.transform_query(
            {"symbol": "AAPL", "start_date": "2026-01-01", "end_date": "2026-01-31"}
        )
        assert str(qp.start_date) == "2026-01-01"
        assert str(qp.end_date) == "2026-01-31"

    def test_multi_symbol(self):
        qp = AlpacaEquityHistoricalFetcher.transform_query(
            {"symbol": "AAPL,MSFT"}
        )
        assert qp.symbol == "AAPL,MSFT"


# ============================================================
# transform_data
# ============================================================

class TestTransformData:
    def test_intraday_returns_datetime_in_ny(self, equity_bars):
        qp = AlpacaEquityHistoricalQueryParams(
            symbol="AAPL", interval="1m"
        )
        results = AlpacaEquityHistoricalFetcher.transform_data(qp, equity_bars)
        assert len(results) == 2
        for r in results:
            assert isinstance(r.date, datetime)
            # America/New_York is UTC-5 in January (EST)
            assert r.date.utcoffset() is not None
            assert r.date.utcoffset().total_seconds() == -5 * 3600

    def test_daily_returns_date(self, equity_daily_bars):
        qp = AlpacaEquityHistoricalQueryParams(
            symbol="AAPL", interval="1d"
        )
        results = AlpacaEquityHistoricalFetcher.transform_data(qp, equity_daily_bars)
        assert len(results) == 2
        for r in results:
            assert isinstance(r.date, date)

    def test_missing_timestamp_skipped(self, equity_daily_bars, bars_without_timestamp):
        qp = AlpacaEquityHistoricalQueryParams(symbol="AAPL")
        results = AlpacaEquityHistoricalFetcher.transform_data(
            qp, equity_daily_bars + bars_without_timestamp
        )
        assert len(results) == 2

    def test_vwap_and_transactions(self, equity_bars):
        qp = AlpacaEquityHistoricalQueryParams(symbol="AAPL", interval="1m")
        results = AlpacaEquityHistoricalFetcher.transform_data(qp, equity_bars)
        assert results[0].vwap == 151.2
        assert results[0].transactions == 50

    def test_multi_symbol_sorted(self, multi_symbol_bars):
        qp = AlpacaEquityHistoricalQueryParams(symbol="AAPL,MSFT", interval="1m")
        results = AlpacaEquityHistoricalFetcher.transform_data(qp, multi_symbol_bars)
        assert len(results) == 2
        symbols = [r.symbol for r in results]
        assert symbols == sorted(symbols)

    def test_sorted_by_date(self, equity_bars):
        qp = AlpacaEquityHistoricalQueryParams(symbol="AAPL", interval="1m")
        results = AlpacaEquityHistoricalFetcher.transform_data(
            qp, list(reversed(equity_bars))
        )
        dates = [r.date for r in results]
        assert dates == sorted(dates)

    def test_adjustment_not_reflected_in_data(self, equity_daily_bars):
        qp = AlpacaEquityHistoricalQueryParams(
            symbol="AAPL", adjustment="splits"
        )
        results = AlpacaEquityHistoricalFetcher.transform_data(qp, equity_daily_bars)
        assert len(results) == 2


# ============================================================
# Data model
# ============================================================

class TestDataModel:
    def test_creation(self):
        d = AlpacaEquityHistoricalData.model_validate({
            "date": "2026-01-02", "open": 150.0, "high": 153.0,
            "low": 149.0, "close": 152.0,
        })
        assert d.open == 150.0
        assert d.close == 152.0
        assert d.high == 153.0
        assert d.low == 149.0

    def test_vwap_optional(self):
        d = AlpacaEquityHistoricalData.model_validate({
            "date": "2026-01-02", "open": 150.0, "high": 153.0,
            "low": 149.0, "close": 152.0,
        })
        assert d.vwap is None

    def test_transactions_optional(self):
        d = AlpacaEquityHistoricalData.model_validate({
            "date": "2026-01-02", "open": 150.0, "high": 153.0,
            "low": 149.0, "close": 152.0,
        })
        assert d.transactions is None

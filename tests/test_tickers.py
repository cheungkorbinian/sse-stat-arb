from datetime import date

import pandas as pd

from sse_data.ingest.yahoo import bars_from_frame
from sse_data.tickers import normalize_ticker, parse_fields, projection_for


def test_normalize_ticker_accepts_common_forms():
    assert normalize_ticker("600000") == "600000.SS"
    assert normalize_ticker("600000.SS") == "600000.SS"
    assert normalize_ticker("sh600000") == "600000.SS"
    assert normalize_ticker("SH:600519") == "600519.SS"


def test_normalize_ticker_rejects_bad_codes():
    try:
        normalize_ticker("AAPL")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_parse_fields_default_and_subset():
    assert parse_fields(None) == ["open", "high", "low", "close", "adj_close", "volume"]
    assert parse_fields("high, low, volume") == ["high", "low", "volume"]


def test_parse_fields_rejects_unknown():
    try:
        parse_fields("high,vwap")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "vwap" in str(exc)


def test_projection_always_includes_date():
    assert projection_for(["high", "volume"]) == {"_id": 0, "date": 1, "high": 1, "volume": 1}


def test_bars_from_frame_maps_yahoo_columns():
    idx = pd.to_datetime(["2010-01-04", "2010-01-05"])
    df = pd.DataFrame(
        {
            "Open": [10.0, 10.2],
            "High": [10.5, 10.6],
            "Low": [9.9, 10.0],
            "Close": [10.1, 10.4],
            "Adj Close": [8.0, 8.2],
            "Volume": [1000, 1100],
        },
        index=idx,
    )
    bars = bars_from_frame("600000", df)
    assert len(bars) == 2
    assert bars[0]["ticker"] == "600000.SS"
    assert bars[0]["high"] == 10.5
    assert bars[0]["volume"] == 1000
    assert bars[0]["date"].date() == date(2010, 1, 4)

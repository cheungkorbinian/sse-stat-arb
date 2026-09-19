from datetime import date

import mongomock

from sse_data.api.queries import query_timeseries
from sse_data.db import ensure_indexes
from sse_data.tickers import date_to_utc


def test_timeseries_filters_by_date_and_fields():
    db = mongomock.MongoClient()["sse_market"]
    ensure_indexes(db)
    db.daily_bars.insert_many(
        [
            {
                "ticker": "600000.SS",
                "date": date_to_utc(date(2010, 1, 4)),
                "high": 10.5,
                "low": 9.9,
                "volume": 1000,
                "close": 10.1,
            },
            {
                "ticker": "600000.SS",
                "date": date_to_utc(date(2010, 1, 5)),
                "high": 10.6,
                "low": 10.0,
                "volume": 1100,
                "close": 10.4,
            },
            {
                "ticker": "600000.SS",
                "date": date_to_utc(date(2010, 1, 6)),
                "high": 11.0,
                "low": 10.2,
                "volume": 1200,
                "close": 10.8,
            },
        ]
    )
    result = query_timeseries(
        db,
        ticker="600000",
        start=date(2010, 1, 4),
        end=date(2010, 1, 5),
        fields="high,volume",
    )
    assert result["ticker"] == "600000.SS"
    assert result["count"] == 2
    assert result["fields"] == ["high", "volume"]
    assert result["data"][0] == {"date": "2010-01-04", "high": 10.5, "volume": 1000}
    assert "low" not in result["data"][0]
    assert result["data"][1]["date"] == "2010-01-05"


def test_timeseries_rejects_inverted_range():
    db = mongomock.MongoClient()["sse_market"]
    try:
        query_timeseries(
            db,
            ticker="600000.SS",
            start=date(2020, 1, 2),
            end=date(2020, 1, 1),
            fields=None,
        )
        assert False, "expected ValueError"
    except ValueError:
        pass

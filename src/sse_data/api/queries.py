from __future__ import annotations

from datetime import date
from typing import Any

from pymongo.database import Database

from sse_data.db import bars_collection, ingest_runs_collection, instruments_collection
from sse_data.tickers import date_to_utc, normalize_ticker, parse_fields, projection_for, to_date


def query_timeseries(
    db: Database,
    *,
    ticker: str,
    start: date,
    end: date,
    fields: str | None = None,
) -> dict[str, Any]:
    if start > end:
        raise ValueError("start date must be on or before end date")
    symbol = normalize_ticker(ticker)
    selected = parse_fields(fields)
    cursor = (
        bars_collection(db)
        .find(
            {
                "ticker": symbol,
                "date": {"$gte": date_to_utc(start), "$lte": date_to_utc(end)},
            },
            projection_for(selected),
        )
        .sort("date", 1)
    )
    series = []
    for doc in cursor:
        row = {"date": to_date(doc["date"]).isoformat()}
        for name in selected:
            if name not in doc:
                continue
            value = doc[name]
            if isinstance(value, float):
                value = round(value, 6)
            row[name] = value
        series.append(row)
    return {
        "ticker": symbol,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "fields": selected,
        "count": len(series),
        "data": series,
    }


def get_instrument(db: Database, ticker: str) -> dict[str, Any] | None:
    doc = instruments_collection(db).find_one(
        {"ticker": normalize_ticker(ticker)},
        {"_id": 0},
    )
    if not doc:
        return None
    if doc.get("list_date"):
        doc["list_date"] = to_date(doc["list_date"]).isoformat()
    if doc.get("updated_at"):
        doc["updated_at"] = doc["updated_at"].isoformat()
    return doc


def list_instruments(db: Database, q: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    filt: dict[str, Any] = {}
    if q:
        filt = {
            "$or": [
                {"ticker": {"$regex": q, "$options": "i"}},
                {"sse_code": {"$regex": q, "$options": "i"}},
                {"name": {"$regex": q, "$options": "i"}},
            ]
        }
    docs = list(
        instruments_collection(db)
        .find(filt, {"_id": 0, "ticker": 1, "sse_code": 1, "name": 1, "share_class": 1, "list_date": 1})
        .sort("sse_code", 1)
        .limit(max(1, min(limit, 500)))
    )
    for doc in docs:
        if doc.get("list_date"):
            doc["list_date"] = to_date(doc["list_date"]).isoformat()
    return docs


def ingest_status(db: Database) -> dict[str, Any]:
    last_run = ingest_runs_collection(db).find_one({}, sort=[("started_at", -1)], projection={"_id": 0})
    if last_run:
        for key in ("started_at", "finished_at"):
            if last_run.get(key):
                last_run[key] = last_run[key].isoformat()
    return {
        "instruments": instruments_collection(db).estimated_document_count(),
        "daily_bars": bars_collection(db).estimated_document_count(),
        "last_run": last_run,
    }

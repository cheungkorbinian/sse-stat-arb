from __future__ import annotations

import time
from datetime import date, timedelta
from typing import Any, Iterable

from pymongo import UpdateOne
from pymongo.database import Database

from sse_data.config import Settings, get_settings
from sse_data.db import (
    bars_collection,
    ensure_indexes,
    ingest_runs_collection,
    ingest_state_collection,
    instruments_collection,
)
from sse_data.ingest.universe import fetch_sse_universe, save_universe_cache
from sse_data.ingest.yahoo import download_bars
from sse_data.tickers import date_to_utc, normalize_ticker, to_date, utc_now


def upsert_instruments(db: Database, instruments: list[dict[str, Any]]) -> int:
    if not instruments:
        return 0
    ops = [
        UpdateOne({"ticker": item["ticker"]}, {"$set": item}, upsert=True)
        for item in instruments
    ]
    result = instruments_collection(db).bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count


def upsert_bars(db: Database, bars: list[dict[str, Any]]) -> int:
    if not bars:
        return 0
    ops = [
        UpdateOne(
            {"ticker": bar["ticker"], "date": bar["date"]},
            {"$set": bar},
            upsert=True,
        )
        for bar in bars
    ]
    result = bars_collection(db).bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count


def last_bar_date(db: Database, ticker: str) -> date | None:
    doc = bars_collection(db).find_one(
        {"ticker": normalize_ticker(ticker)},
        sort=[("date", -1)],
        projection={"date": 1},
    )
    if not doc:
        return None
    return to_date(doc["date"])


def _record_state(
    db: Database,
    ticker: str,
    *,
    last_date: date | None,
    bars_count: int,
    error: str | None = None,
) -> None:
    ingest_state_collection(db).update_one(
        {"ticker": ticker},
        {
            "$set": {
                "ticker": ticker,
                "last_date": date_to_utc(last_date) if last_date else None,
                "bars_count": bars_count,
                "last_error": error,
                "updated_at": utc_now(),
            }
        },
        upsert=True,
    )


def _chunked(items: list[str], size: int) -> Iterable[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _start_for_ticker(db: Database, ticker: str, history_start: date) -> date:
    last = last_bar_date(db, ticker)
    if last is None:
        return history_start
    return last + timedelta(days=1)


def _refresh_universe(db: Database, include_b_shares: bool) -> list[dict[str, Any]]:
    instruments = fetch_sse_universe(include_b_shares=include_b_shares)
    if not instruments:
        raise RuntimeError("SSE universe download returned no instruments")
    upsert_instruments(db, instruments)
    save_universe_cache(instruments)
    return instruments


def _selected_tickers(
    instruments: list[dict[str, Any]],
    tickers: list[str] | None,
    limit: int | None,
) -> list[str]:
    if tickers:
        return [normalize_ticker(t) for t in tickers]
    symbols = [item["ticker"] for item in instruments]
    if limit is not None:
        return symbols[: max(limit, 0)]
    return symbols


def _instruments_from_tickers(tickers: list[str]) -> list[dict[str, Any]]:
    now = utc_now()
    return [
        {
            "ticker": ticker,
            "sse_code": ticker.removesuffix(".SS"),
            "exchange": "SSE",
            "source": "manual",
            "updated_at": now,
        }
        for ticker in tickers
    ]


def _resolve_tickers(
    db: Database,
    tickers: list[str] | None,
    limit: int | None,
    include_b_shares: bool,
) -> list[str]:
    if tickers:
        selected = [normalize_ticker(t) for t in tickers]
        upsert_instruments(db, _instruments_from_tickers(selected))
        return selected
    try:
        instruments = _refresh_universe(db, include_b_shares)
    except Exception as exc:
        existing = list(
            instruments_collection(db).find({}, {"ticker": 1, "_id": 0}).sort("sse_code", 1)
        )
        if not existing:
            raise RuntimeError(f"could not refresh SSE universe: {exc}") from exc
        instruments = existing
    return _selected_tickers(instruments, None, limit)


def ingest_tickers(
    db: Database,
    tickers: list[str],
    *,
    settings: Settings | None = None,
    kind: str = "update",
) -> dict[str, Any]:
    settings = settings or get_settings()
    ensure_indexes(db)
    started = utc_now()
    today = date.today()
    bars_col = bars_collection(db)
    ok = empty = failed = upserted = 0
    errors: list[dict[str, str]] = []

    for batch in _chunked(tickers, settings.yahoo_batch_size):
        starts = {ticker: _start_for_ticker(db, ticker, settings.history_start) for ticker in batch}
        pending = [ticker for ticker, start in starts.items() if start <= today]
        if not pending:
            ok += len(batch)
            continue
        earliest = min(starts[ticker] for ticker in pending)
        try:
            downloaded = download_bars(pending, start=earliest, end=today)
        except Exception as exc:  # noqa: BLE001 - Yahoo is flaky; isolate a batch
            for ticker in pending:
                failed += 1
                errors.append({"ticker": ticker, "error": str(exc)})
                _record_state(
                    db,
                    ticker,
                    last_date=last_bar_date(db, ticker),
                    bars_count=bars_col.count_documents({"ticker": ticker}),
                    error=str(exc),
                )
            time.sleep(settings.yahoo_pause_seconds)
            continue

        for ticker in pending:
            rows = [
                bar
                for bar in downloaded.get(ticker, [])
                if to_date(bar["date"]) >= starts[ticker]
            ]
            try:
                written = upsert_bars(db, rows)
                count = bars_col.count_documents({"ticker": ticker})
                last = last_bar_date(db, ticker)
                _record_state(db, ticker, last_date=last, bars_count=count, error=None)
                upserted += written
                if rows:
                    ok += 1
                else:
                    empty += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                errors.append({"ticker": ticker, "error": str(exc)})
                _record_state(
                    db,
                    ticker,
                    last_date=last_bar_date(db, ticker),
                    bars_count=bars_col.count_documents({"ticker": ticker}),
                    error=str(exc),
                )

        time.sleep(settings.yahoo_pause_seconds)

    summary = {
        "kind": kind,
        "started_at": started,
        "finished_at": utc_now(),
        "tickers_total": len(tickers),
        "tickers_ok": ok,
        "tickers_empty": empty,
        "tickers_failed": failed,
        "bars_upserted": upserted,
        "errors": errors[:50],
    }
    ingest_runs_collection(db).insert_one(dict(summary))
    return summary


def bootstrap(
    db: Database,
    *,
    tickers: list[str] | None = None,
    limit: int | None = None,
    include_b_shares: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Initial load of SSE daily bars since HISTORY_START (resume-safe)."""
    settings = settings or get_settings()
    ensure_indexes(db)
    selected = _resolve_tickers(db, tickers, limit, include_b_shares)
    return ingest_tickers(db, selected, settings=settings, kind="bootstrap")


def update_daily(
    db: Database,
    *,
    tickers: list[str] | None = None,
    include_b_shares: bool = False,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Incremental update from each ticker's last stored date through today."""
    settings = settings or get_settings()
    ensure_indexes(db)
    selected = _resolve_tickers(db, tickers, None, include_b_shares)
    return ingest_tickers(db, selected, settings=settings, kind="update")

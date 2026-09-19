from __future__ import annotations

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
from pymongo.database import Database

from sse_data.db import bars_collection
from sse_data.tickers import normalize_ticker, to_date


def _as_utc(value: date) -> datetime:
    return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)


def load_price_panel(
    db: Database,
    tickers: list[str],
    *,
    start: date | None = None,
    end: date | None = None,
    field: str = "adj_close",
) -> pd.DataFrame:
    """Wide panel of daily prices indexed by date, columns = Yahoo tickers."""
    symbols = [normalize_ticker(t) for t in tickers]
    filt: dict = {"ticker": {"$in": symbols}}
    if start or end:
        date_filt: dict = {}
        if start:
            date_filt["$gte"] = _as_utc(start)
        if end:
            date_filt["$lte"] = _as_utc(end)
        filt["date"] = date_filt

    rows = list(bars_collection(db).find(filt, {"_id": 0, "ticker": 1, "date": 1, field: 1}))
    if not rows:
        return pd.DataFrame()

    frame = pd.DataFrame(rows)
    frame["date"] = frame["date"].map(to_date)
    panel = frame.pivot(index="date", columns="ticker", values=field).sort_index()
    panel.index = pd.to_datetime(panel.index)
    return panel.astype(float)


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return np.log(prices.where(prices > 0)).diff()


def aligned_log_prices(prices: pd.DataFrame, min_obs: int = 252) -> pd.DataFrame:
    """Keep columns with enough history; forward-fill small gaps only."""
    clean = prices.mask(prices <= 0).ffill(limit=3)
    keep = [col for col in clean.columns if int(clean[col].notna().sum()) >= min_obs]
    return clean[keep]

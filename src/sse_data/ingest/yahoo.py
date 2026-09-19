from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import yfinance as yf

from sse_data.tickers import date_to_utc, normalize_ticker, utc_now

PRICE_COLUMNS = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "Volume": "volume",
}


def _flatten_ticker_frame(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if not isinstance(df.columns, pd.MultiIndex):
        return df
    level0 = list(df.columns.get_level_values(0).unique())
    level1 = list(df.columns.get_level_values(1).unique())
    if ticker in level0:
        return df[ticker]
    if ticker in level1:
        return df.xs(ticker, axis=1, level=1)
    if len(level0) == 1:
        return df[level0[0]]
    return pd.DataFrame()


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    renamed = {}
    for col in df.columns:
        name = str(col)
        renamed[col] = PRICE_COLUMNS.get(name, name.strip().lower().replace(" ", "_"))
    out = df.rename(columns=renamed)
    keep = [name for name in PRICE_COLUMNS.values() if name in out.columns]
    return out[keep]


def bars_from_frame(ticker: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    ticker = normalize_ticker(ticker)
    frame = _normalize_columns(_flatten_ticker_frame(df, ticker))
    if frame.empty:
        return []
    frame = frame.copy()
    frame = frame.dropna(how="all")
    if "close" in frame.columns:
        frame = frame.dropna(subset=["close"])
    bars: list[dict[str, Any]] = []
    for idx, row in frame.iterrows():
        ts = pd.Timestamp(idx).to_pydatetime()
        bar: dict[str, Any] = {
            "ticker": ticker,
            "date": date_to_utc(ts),
            "source": "yahoo",
            "updated_at": utc_now(),
        }
        for field in PRICE_COLUMNS.values():
            if field not in row.index or pd.isna(row[field]):
                continue
            value = row[field]
            bar[field] = int(value) if field == "volume" else round(float(value), 6)
        if "close" not in bar:
            continue
        bars.append(bar)
    return bars


def download_bars(
    tickers: list[str],
    start: date,
    end: date | None = None,
    pause_after: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Download Yahoo daily OHLCV. `end` is inclusive."""
    symbols = [normalize_ticker(t) for t in tickers]
    yahoo_end = None if end is None else end + timedelta(days=1)
    frame = yf.download(
        tickers=symbols if len(symbols) > 1 else symbols[0],
        start=start.isoformat(),
        end=None if yahoo_end is None else yahoo_end.isoformat(),
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    result: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    if frame is None or getattr(frame, "empty", True):
        return result
    for symbol in symbols:
        if len(symbols) == 1 and not isinstance(frame.columns, pd.MultiIndex):
            result[symbol] = bars_from_frame(symbol, frame)
        else:
            result[symbol] = bars_from_frame(symbol, frame)
    return result

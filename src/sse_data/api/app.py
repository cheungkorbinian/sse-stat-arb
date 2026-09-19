from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from sse_data import __version__
from sse_data.api.queries import get_instrument, ingest_status, list_instruments, query_timeseries
from sse_data.db import ensure_indexes, get_client, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    client = get_client()
    app.state.mongo = client
    app.state.db = get_db(client)
    try:
        client.admin.command("ping")
        ensure_indexes(app.state.db)
    except Exception as exc:  # noqa: BLE001
        client.close()
        raise RuntimeError(
            "Cannot reach MongoDB. Start it first, then retry. "
            "See README.md for Homebrew / Docker instructions."
        ) from exc
    yield
    client.close()


app = FastAPI(
    title="SSE Market Data API",
    description=(
        "Task 1 REST API for Shanghai Stock Exchange daily bars stored in MongoDB. "
        "Built to be extended for pairs trading and statistical arbitrage."
    ),
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    app.state.mongo.admin.command("ping")
    return {"status": "ok"}


@app.get("/v1/timeseries")
def timeseries(
    ticker: Annotated[str, Query(description="SSE ticker, e.g. 600000 or 600000.SS")],
    start: Annotated[date, Query(description="Inclusive start date YYYY-MM-DD")],
    end: Annotated[date, Query(description="Inclusive end date YYYY-MM-DD")],
    fields: Annotated[
        str | None,
        Query(description="Comma-separated fields: open,high,low,close,adj_close,volume"),
    ] = None,
) -> JSONResponse:
    try:
        payload = query_timeseries(
            app.state.db,
            ticker=ticker,
            start=start,
            end=end,
            fields=fields,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(payload)


@app.get("/v1/instruments")
def instruments(
    q: Annotated[str | None, Query(description="Search code or name")] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
) -> dict:
    return {"items": list_instruments(app.state.db, q=q, limit=limit)}


@app.get("/v1/instruments/{ticker}")
def instrument(ticker: str) -> dict:
    try:
        doc = get_instrument(app.state.db, ticker)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not doc:
        raise HTTPException(status_code=404, detail=f"instrument not found: {ticker}")
    return doc


@app.get("/v1/ingest/status")
def status() -> dict:
    return ingest_status(app.state.db)

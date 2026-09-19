# SSE Statistical Arbitrage Research Stack

End-to-end **statistical arbitrage research pipeline** for liquid Shanghai A-shares (SSE): market data ingest, MongoDB storage, REST API, correlation clustering, cointegration-based pair selection, and rolling walk-forward backtests with A-share transaction costs and T+1 execution.


## Highlights

- **Data layer:** Yahoo Finance daily bars since 2010 → MongoDB with resume-safe bootstrap and incremental updates
- **API:** FastAPI time-series endpoint for research and ops (`/v1/timeseries`, instrument lookup, ingest status)
- **Research:** Mantegna distance + hierarchical clustering (7 groups), Engle–Granger pair selection (|ρ| ≥ 0.5, p < 0.05), z-score mean-reversion
- **Backtest:** 41 rolling windows (252-day formation / 63-day trading), commission + stamp duty + slippage, T+1 discipline
- **Sample run:** 137 round-trip trades over 10+ years of simulated history (see `data/research/task2_results.json`)

## Architecture

```
Yahoo Finance / East Money universe
        ↓
  ingest pipeline (bootstrap + daily update)
        ↓
     MongoDB (instruments, daily_bars, ingest_state)
        ↓
  FastAPI REST API  ←→  research module (cluster → pairs → backtest)
```

## Layout

```
src/sse_data/
  db.py              MongoDB client, collections, indexes
  tickers.py         ticker / field helpers
  ingest/universe.py SSE instrument list
  ingest/yahoo.py    Yahoo daily download
  ingest/pipeline.py bootstrap + incremental update
  api/app.py         FastAPI app
  api/queries.py     time-series query used by the API
  research/          correlation, clustering, pairs, strategy, backtest
  cli.py             sse-data bootstrap | update | serve | research | status
```

## Setup

Python 3.11+ and MongoDB on `localhost:27017`.

```bash
git clone https://github.com/KorbinianCheung/sse-stat-arb.git
cd sse-stat-arb
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### MongoDB

**Portable binary (no Docker / Homebrew required):**

```bash
chmod +x scripts/start-mongo.sh
./scripts/start-mongo.sh
```

Docker:

```bash
docker compose up -d
```

## Load data

Smoke test (five liquid names):

```bash
sse-data bootstrap --tickers 600000,600519,601318,600036,601398
sse-data status
```

Research universe (35 liquid SSE names):

```bash
sse-data bootstrap --tickers 600000,600009,600016,600019,600028,600030,600031,600036,600048,600104,600276,600519,600585,600690,600809,600887,600900,601088,601166,601288,601318,601328,601390,601398,601601,601628,601633,601668,601688,601766,601818,601857,601899,601939,601988
sse-data update
```

## REST API

```bash
sse-data serve
```

Docs: http://127.0.0.1:8000/docs

```bash
curl "http://127.0.0.1:8000/v1/timeseries?ticker=600000.SS&start=2024-01-01&end=2024-01-31&fields=high,low,volume"
```

## Research & backtest

Methodology (formulas): [`docs/TASK2_METHODS.md`](docs/TASK2_METHODS.md)

```bash
sse-data research
```

Outputs:

- `data/research/task2_results.json`
- `docs/SSE_StatArb_Slides.pptx`

## Tests

```bash
pytest -q
```


## Author

**Korbinian Cheung** — HKU BEng AI & Data Science  
GitHub: [KorbinianCheung](https://github.com/KorbinianCheung)

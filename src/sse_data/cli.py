from __future__ import annotations

import argparse
import json
from datetime import date, datetime

import uvicorn

from sse_data.config import get_settings
from sse_data.db import get_client, get_db
from sse_data.ingest.pipeline import bootstrap, update_daily
from sse_data.api.queries import ingest_status
from sse_data.research.run import run_task2
from sse_data.research.universe import SSE_RESEARCH_UNIVERSE


def _json_default(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _print(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))


def _split_tickers(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    return [part.strip() for part in raw.split(",") if part.strip()]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sse-data",
        description="SSE daily market-data system (MongoDB + Yahoo Finance + REST API)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    boot = sub.add_parser("bootstrap", help="Load SSE universe and historical daily bars since 2010")
    boot.add_argument("--tickers", help="Comma-separated tickers (e.g. 600000,600519)")
    boot.add_argument("--limit", type=int, help="Only ingest the first N universe tickers (smoke test)")
    boot.add_argument("--include-b-shares", action="store_true")

    upd = sub.add_parser("update", help="Incrementally fetch new daily bars through today")
    upd.add_argument("--tickers", help="Comma-separated tickers; default is the full SSE universe")
    upd.add_argument("--include-b-shares", action="store_true")

    sub.add_parser("status", help="Print MongoDB ingest status")
    serve = sub.add_parser("serve", help="Start the REST API")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)

    research = sub.add_parser("research", help="Run Task 2: correlate, cluster, backtest mean-reversion")
    research.add_argument("--tickers", help="Comma-separated tickers; default is the liquid SSE research universe")
    research.add_argument("--start", default="2015-01-01", help="Walk-forward start date")
    research.add_argument("--end", help="Walk-forward end date")
    research.add_argument("--formation-days", type=int, default=252)
    research.add_argument("--trade-days", type=int, default=63)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    settings = get_settings()

    if args.command == "serve":
        uvicorn.run(
            "sse_data.api.app:app",
            host=args.host or settings.api_host,
            port=args.port or settings.api_port,
            reload=False,
        )
        return

    client = get_client(settings)
    try:
        client.admin.command("ping")
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f"Cannot reach MongoDB at {settings.mongodb_uri}. {exc}"
        ) from exc
    db = get_db(client, settings)

    if args.command == "bootstrap":
        summary = bootstrap(
            db,
            tickers=_split_tickers(args.tickers),
            limit=args.limit,
            include_b_shares=args.include_b_shares,
            settings=settings,
        )
        _print(summary)
    elif args.command == "update":
        summary = update_daily(
            db,
            tickers=_split_tickers(args.tickers),
            include_b_shares=args.include_b_shares,
            settings=settings,
        )
        _print(summary)
    elif args.command == "status":
        _print(ingest_status(db))
    elif args.command == "research":
        start = date.fromisoformat(args.start) if args.start else None
        end = date.fromisoformat(args.end) if args.end else None
        tickers = _split_tickers(args.tickers) or SSE_RESEARCH_UNIVERSE
        result = run_task2(
            db,
            tickers=tickers,
            start=start,
            end=end,
            formation_days=args.formation_days,
            trade_days=args.trade_days,
        )
        _print(
            {
                "metrics": result["metrics"],
                "k_clusters": (result.get("clusters") or {}).get("k"),
                "n_names": result.get("n_names"),
                "results": "data/research/task2_results.json",
            }
        )
    client.close()

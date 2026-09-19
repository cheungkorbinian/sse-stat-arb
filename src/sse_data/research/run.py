from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from pymongo.database import Database

from sse_data.research.backtest import walk_forward
from sse_data.research.prices import load_price_panel
from sse_data.research.strategy import StrategyConfig
from sse_data.research.universe import SSE_RESEARCH_UNIVERSE
from sse_data.tickers import normalize_ticker

RESULTS_PATH = Path("data/research/task2_results.json")


def run_task2(
    db: Database,
    *,
    tickers: list[str] | None = None,
    start: date | None = date(2015, 1, 1),
    end: date | None = None,
    formation_days: int = 252,
    trade_days: int = 63,
    out: Path = RESULTS_PATH,
) -> dict[str, Any]:
    names = tickers or SSE_RESEARCH_UNIVERSE
    prices = load_price_panel(db, names, start=date(2010, 1, 1), end=end)
    if prices.empty:
        raise RuntimeError("no prices in MongoDB — run: sse-data bootstrap --tickers <list>")
    result = walk_forward(
        prices,
        formation_days=formation_days,
        trade_days=trade_days,
        cfg=StrategyConfig(),
        start=start,
        end=end,
    )
    result["universe"] = [normalize_ticker(t) for t in names]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    _write_slides(result)
    return result


def _write_slides(result: dict[str, Any]) -> None:
    import importlib.util

    script = Path(__file__).resolve().parents[3] / "scripts" / "build_slides.py"
    spec = importlib.util.spec_from_file_location("task2_slides", script)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.build(result)

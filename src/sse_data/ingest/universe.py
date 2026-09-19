from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import httpx

from sse_data.tickers import is_sse_a_share, is_sse_b_share, normalize_ticker, sse_code, utc_now

EASTMONEY_URL = "https://push2.eastmoney.com/api/qt/clist/get"
CACHE_PATH = Path("data/cache/sse_universe.json")
PAGE_SIZE = 100


def _parse_list_date(raw: Any) -> date | None:
    if raw in (None, "", "-", 0, "0"):
        return None
    text = str(int(raw)) if isinstance(raw, (int, float)) else str(raw).strip()
    if len(text) != 8 or not text.isdigit():
        return None
    return date(int(text[:4]), int(text[4:6]), int(text[6:8]))


def _page_params(page: int, include_b_shares: bool) -> dict[str, Any]:
    boards = "m:1+t:2,m:1+t:23"
    if include_b_shares:
        boards = f"{boards},m:1+t:8"
    return {
        "pn": page,
        "pz": PAGE_SIZE,
        "po": 1,
        "np": 1,
        "fltt": 2,
        "invt": 2,
        "fid": "f12",
        "fs": boards,
        "fields": "f12,f14,f26",
    }


def fetch_sse_universe(include_b_shares: bool = False, timeout: float = 30.0) -> list[dict[str, Any]]:
    """List SSE equities from East Money, mapped to Yahoo `.SS` tickers."""
    instruments: list[dict[str, Any]] = []
    seen: set[str] = set()
    headers = {
        "Referer": "https://quote.eastmoney.com/",
        "User-Agent": "Mozilla/5.0 sse-stat-arb/0.1",
    }
    with httpx.Client(timeout=timeout, headers=headers) as client:
        page = 1
        total = None
        while True:
            response = client.get(EASTMONEY_URL, params=_page_params(page, include_b_shares))
            response.raise_for_status()
            payload = response.json()
            data = (payload or {}).get("data") or {}
            rows = data.get("diff") or []
            if total is None:
                total = int(data.get("total") or 0)
            if not rows:
                break
            for row in rows:
                code = str(row.get("f12") or "").zfill(6)
                if include_b_shares:
                    if not (is_sse_a_share(code) or is_sse_b_share(code)):
                        continue
                elif not is_sse_a_share(code):
                    continue
                ticker = normalize_ticker(code)
                if ticker in seen:
                    continue
                seen.add(ticker)
                instruments.append(
                    {
                        "ticker": ticker,
                        "sse_code": sse_code(ticker),
                        "exchange": "SSE",
                        "name": str(row.get("f14") or "").strip(),
                        "list_date": _parse_list_date(row.get("f26")),
                        "share_class": "B" if is_sse_b_share(code) else "A",
                        "source": "eastmoney",
                        "updated_at": utc_now(),
                    }
                )
            if (total and len(instruments) >= total) or len(rows) < PAGE_SIZE:
                break
            page += 1
            if page > 80:
                break
    instruments.sort(key=lambda item: item["sse_code"])
    return instruments


def save_universe_cache(instruments: list[dict[str, Any]], path: Path = CACHE_PATH) -> None:
    import json

    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for item in instruments:
        row = dict(item)
        if isinstance(row.get("list_date"), date):
            row["list_date"] = row["list_date"].isoformat()
        if hasattr(row.get("updated_at"), "isoformat"):
            row["updated_at"] = row["updated_at"].isoformat()
        serializable.append(row)
    path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def load_universe_cache(path: Path = CACHE_PATH) -> list[dict[str, Any]]:
    import json
    from datetime import datetime

    if not path.exists():
        raise FileNotFoundError(f"universe cache not found: {path}")
    rows = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for row in rows:
        if row.get("list_date"):
            row["list_date"] = date.fromisoformat(row["list_date"])
        if row.get("updated_at"):
            row["updated_at"] = datetime.fromisoformat(row["updated_at"])
        out.append(row)
    return out

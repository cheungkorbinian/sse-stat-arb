from __future__ import annotations

import re
from datetime import date, datetime, timezone

YAHOO_SUFFIX = ".SS"
ALLOWED_BAR_FIELDS = ("open", "high", "low", "close", "adj_close", "volume")
SSE_A_PREFIXES = ("60", "68")  # 600/601/603/605 main board, 688 STAR
SSE_B_PREFIX = "900"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_date(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def date_to_utc(value: date | datetime | str) -> datetime:
    d = to_date(value)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def normalize_ticker(raw: str) -> str:
    """Accept 600000, 600000.SS, sh600000, SH600000 and return Yahoo SSE form."""
    if raw is None:
        raise ValueError("ticker is required")
    text = str(raw).strip().upper().replace(" ", "")
    if not text:
        raise ValueError("ticker is required")

    text = re.sub(r"^(SH|SSE)[:\.]?", "", text)
    text = text.removesuffix(".SS").removesuffix(".SHA")
    digits = re.sub(r"\D", "", text)
    if len(digits) != 6 or not digits.isdigit():
        raise ValueError(f"invalid SSE ticker: {raw!r}")
    return f"{digits}{YAHOO_SUFFIX}"


def sse_code(ticker: str) -> str:
    return normalize_ticker(ticker).removesuffix(YAHOO_SUFFIX)


def is_sse_a_share(code: str) -> bool:
    return len(code) == 6 and code.startswith(SSE_A_PREFIXES)


def is_sse_b_share(code: str) -> bool:
    return len(code) == 6 and code.startswith(SSE_B_PREFIX)


def parse_fields(raw: str | None) -> list[str]:
    if raw is None or str(raw).strip() == "":
        return list(ALLOWED_BAR_FIELDS)
    requested = [part.strip().lower() for part in str(raw).split(",") if part.strip()]
    unknown = [name for name in requested if name not in ALLOWED_BAR_FIELDS]
    if unknown:
        allowed = ", ".join(ALLOWED_BAR_FIELDS)
        raise ValueError(f"unsupported fields {unknown}; allowed: {allowed}")
    seen: list[str] = []
    for name in requested:
        if name not in seen:
            seen.append(name)
    return seen


def projection_for(fields: list[str]) -> dict[str, int]:
    projection = {"_id": 0, "date": 1}
    for name in fields:
        projection[name] = 1
    return projection

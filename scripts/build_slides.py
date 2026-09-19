#!/usr/bin/env python3
"""Course submission PowerPoint — dense layout, short explanations on every slide."""

from __future__ import annotations

import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/research/task2_results.json"
OUT = ROOT / "docs/SSE_StatArb_Slides.pptx"
ALT = ROOT / "docs/Task2_Slides.pptx"

NAVY = RGBColor(0x0F, 0x2A, 0x43)
ACCENT = RGBColor(0x1F, 0x6F, 0x8B)
GOLD = RGBColor(0xB8, 0x86, 0x0B)
RED = RGBColor(0xA3, 0x3B, 0x3B)
INK = RGBColor(0x1C, 0x1C, 0x1C)
MUTED = RGBColor(0x4A, 0x4A, 0x4A)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PAPER = RGBColor(0xF4, 0xF1, 0xEA)
CARD = RGBColor(0xE8, 0xEE, 0xF2)
LINE = RGBColor(0xC9, 0xC4, 0xBA)
SOFT = RGBColor(0xC8, 0xD0, 0xD8)

W = Inches(13.333)
H = Inches(7.5)


def _fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _box(slide, l, t, w, h, fill, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    _fill(sh, fill)
    if line is not None:
        sh.line.color.rgb = line
        sh.line.width = Pt(0.75)
    else:
        sh.line.fill.background()
    try:
        sh.adjustments[0] = 0.06
    except Exception:
        pass
    return sh


def _tb(slide, l, t, w, h, text, *, size=14, bold=False, color=INK, align=PP_ALIGN.LEFT, font="Calibri"):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font
    return box


def _plist(slide, l, t, w, h, items, *, size=13, color=INK, gap=6):
    box = slide.shapes.add_textbox(l, t, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(gap)
        p.space_before = Pt(0)
        run = p.add_run()
        run.text = "•  " + item
        run.font.size = Pt(size)
        run.font.color.rgb = color
        run.font.name = "Calibri"
    return box


def _footer(slide, n, total):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(7.28), W, Inches(0.22))
    _fill(bar, NAVY)
    _tb(slide, Inches(0.4), Inches(7.28), Inches(10), Inches(0.22),
        "Asia Quant Academy  ·  SSE statistical arbitrage  ·  17 August 2026",
        size=10, color=WHITE)
    _tb(slide, Inches(11.7), Inches(7.28), Inches(1.2), Inches(0.22),
        f"{n} / {total}", size=10, color=WHITE, align=PP_ALIGN.RIGHT)


def _header(slide, kicker, title, intro):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), W, Inches(0.68))
    _fill(bar, NAVY)
    gold = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0.68), W, Inches(0.05))
    _fill(gold, GOLD)
    _tb(slide, Inches(0.4), Inches(0.04), Inches(12.5), Inches(0.22), kicker, size=10, bold=True, color=GOLD)
    _tb(slide, Inches(0.4), Inches(0.24), Inches(12.5), Inches(0.4), title, size=22, bold=True, color=WHITE)
    _box(slide, Inches(0.35), Inches(0.84), Inches(12.63), Inches(0.62), WHITE, LINE)
    _tb(slide, Inches(0.5), Inches(0.88), Inches(12.4), Inches(0.54), intro, size=13, color=MUTED)


def _blank(prs):
    s = prs.slides.add_slide(prs.slide_layouts[6])
    bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), W, H)
    _fill(bg, PAPER)
    return s


def _table(slide, l, t, w, h, headers, rows, col_w=None, size=12):
    table = slide.shapes.add_table(1 + len(rows), len(headers), l, t, w, h).table
    if col_w:
        for i, width in enumerate(col_w):
            table.columns[i].width = width
    for j, htxt in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = htxt
        cell.fill.solid()
        cell.fill.fore_color.rgb = NAVY
        for p in cell.text_frame.paragraphs:
            p.font.size = Pt(size)
            p.font.bold = True
            p.font.color.rgb = WHITE
            p.font.name = "Calibri"
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.text_frame.word_wrap = True
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            cell = table.cell(i, j)
            cell.text = str(val)
            cell.fill.solid()
            cell.fill.fore_color.rgb = WHITE if i % 2 else CARD
            for p in cell.text_frame.paragraphs:
                p.font.size = Pt(size)
                p.font.color.rgb = INK
                p.font.name = "Calibri"
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.text_frame.word_wrap = True
    return table


def _theme(tickers: list[str]) -> str:
    codes = {t.replace(".SS", "")[:6] for t in tickers}
    if {"600519", "600809"} & codes:
        return "Consumer / liquor"
    if {"600028", "601857", "601088"} & codes and len(codes) <= 4:
        return "Energy"
    if {"601318", "601601", "601628"} & codes:
        return "Insurance / brokers"
    if {"600104", "601633"} & codes and len(codes) <= 3:
        return "Auto"
    if len(codes) == 1 and "600276" in codes:
        return "Pharma"
    if {"601398", "601988", "600036", "601939"} & codes:
        return "Banks / rates"
    return "Industrials / materials"


def _names(tickers: list[str], limit: int = 6) -> str:
    label = {
        "600000": "SPD Bank", "600009": "SH Airport", "600016": "Minsheng",
        "600019": "Baosteel", "600028": "Sinopec", "600030": "CITIC Sec",
        "600031": "Sany", "600036": "CMB", "600048": "Poly", "600104": "SAIC",
        "600276": "Hengrui", "600519": "Moutai", "600585": "Conch",
        "600690": "Haier", "600809": "Fenjiu", "600887": "Yili",
        "600900": "Yangtze Power", "601088": "Shenhua", "601166": "Industrial Bk",
        "601288": "ABC", "601318": "Ping An", "601328": "BoComm",
        "601390": "China Railway", "601398": "ICBC", "601601": "CPIC",
        "601628": "China Life", "601633": "Great Wall", "601668": "CSCEC",
        "601688": "Huatai", "601766": "CRRC", "601818": "Everbright",
        "601857": "PetroChina", "601899": "Zijin", "601939": "CCB", "601988": "BOC",
    }
    pretty = [label.get(t.replace(".SS", "")[:6], t.replace(".SS", "")[:6]) for t in tickers]
    if len(pretty) > limit:
        return ", ".join(pretty[:limit]) + "…"
    return ", ".join(pretty)


def build(results: dict) -> None:
    m = results.get("metrics") or {}
    clusters = results.get("clusters") or {}
    groups = clusters.get("groups") or []
    top = results.get("top_correlations") or []
    eq = results.get("equity_monthly") or []
    by_year = {str(row["date"])[:4]: float(row["equity"]) for row in eq}
    years = sorted(by_year)
    eq_cats = ["Start", *years]
    eq_vals = [1.0, *[by_year[y] for y in years]]
    n_names = results.get("n_names", 35)
    sample = f"{str(results.get('equity_start', ''))[:10]} → {str(results.get('equity_end', ''))[:10]}"
    rho0 = float(top[0]["rho"]) if top else 0.844
    d0 = (2.0 * (1.0 - rho0)) ** 0.5
    py = _names([top[0]["y"]]) if top else "Ping An"
    px = _names([top[0]["x"]]) if top else "CPIC"

    prs = Presentation()
    prs.slide_width = W
    prs.slide_height = H
    total = 18

    # —— 1 Title ——
    s = prs.slides.add_slide(prs.slide_layouts[6])
    _fill(s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), W, H), NAVY)
    _fill(s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), H), GOLD)
    _tb(s, Inches(0.55), Inches(0.45), Inches(12), Inches(0.3),
        "ASIA QUANT ACADEMY  ·  WEEKLY TASK  ·  17 AUGUST 2026", size=13, bold=True, color=GOLD)
    _tb(s, Inches(0.55), Inches(0.85), Inches(12.2), Inches(1.15),
        "Statistical arbitrage on the\nShanghai Stock Exchange", size=32, bold=True, color=WHITE)
    _tb(s, Inches(0.55), Inches(2.15), Inches(12.2), Inches(0.7),
        "Build a reusable market-data system first, then test whether a classic pairs / mean-reversion\n"
        "strategy has an edge on China A-shares after realistic costs.",
        size=15, color=SOFT)
    steps = [
        ("01", "Store", "SSE daily bars since 2010 in MongoDB, with a unique (ticker, date) index."),
        ("02", "Serve", "REST API: start, end, ticker, fields → time series. Cron updater."),
        ("03", "Cluster", "Correlate log returns, convert to distance, group similar names."),
        ("04", "Trade", "Cointegrated pairs, z-score mean reversion, walk-forward backtest."),
    ]
    for i, (num, title, blurb) in enumerate(steps):
        left = Inches(0.45 + i * 3.2)
        _box(s, left, Inches(3.15), Inches(3.05), Inches(2.85), RGBColor(0x16, 0x38, 0x54))
        _tb(s, left + Inches(0.15), Inches(3.28), Inches(2.75), Inches(0.35), num, size=12, bold=True, color=GOLD)
        _tb(s, left + Inches(0.15), Inches(3.58), Inches(2.75), Inches(0.4), title, size=20, bold=True, color=WHITE)
        _tb(s, left + Inches(0.15), Inches(4.1), Inches(2.75), Inches(1.65), blurb, size=13, color=SOFT)
    _tb(s, Inches(0.55), Inches(6.2), Inches(12), Inches(0.7),
        "Prices: Yahoo Finance adjusted close (.SS). Universe list: East Money SSE A + STAR.\n"
        "Add your name here before upload.  Repo: sse-stat-arb.",
        size=13, color=GOLD)
    _footer(s, 1, total)

    # —— 2 Agenda ——
    s = _blank(prs)
    _header(s, "OVERVIEW", "The brief, in the order we built it",
            "The email asks for a data layer that future weeks can reuse, plus a first look at statistical arbitrage. "
            "We therefore split the work: persist and serve history, then research on top of the same API.")
    _box(s, Inches(0.35), Inches(1.6), Inches(6.25), Inches(5.45), WHITE, LINE)
    _tb(s, Inches(0.55), Inches(1.72), Inches(5.9), Inches(0.35), "Data system  (must survive later tasks)", size=16, bold=True, color=NAVY)
    _plist(s, Inches(0.55), Inches(2.15), Inches(5.9), Inches(3.4), [
        "MongoDB holds every SSE daily bar we ingest. One document = one ticker on one day.",
        "REST GET /v1/timeseries is the contract in the brief: start, end, ticker, fields.",
        "sse-data bootstrap loads history since 2010; sse-data update fills new days.",
        "Unique (ticker, date) means a rerun overwrites, it never duplicates.",
        "Research never writes into daily_bars — clustering/backtest are separate.",
    ], size=13, gap=10)
    _tb(s, Inches(0.55), Inches(5.65), Inches(5.9), Inches(1.2),
        "Why this shape: next week you can add pairs or factors without migrating the database or breaking the API.",
        size=13, color=MUTED)
    _box(s, Inches(6.75), Inches(1.6), Inches(6.2), Inches(5.45), WHITE, LINE)
    _tb(s, Inches(6.95), Inches(1.72), Inches(5.8), Inches(0.35), "Strategy  (A → B → C → D)", size=16, bold=True, color=NAVY)
    _plist(s, Inches(6.95), Inches(2.15), Inches(5.8), Inches(3.4), [
        "A  Correlate daily log returns. Turn ρ into a distance so we can cluster.",
        "B  Average-linkage clustering. Check that groups look like banks, energy, liquor.",
        "C  Inside a cluster, keep cointegrated pairs and trade the residual with a z-score.",
        "D  Walk-forward backtest, net of A-share costs, fill at t+1 (T+1).",
        "Result: clusters are economic; the trade does not beat costs on mega-caps.",
    ], size=13, gap=10)
    _tb(s, Inches(6.95), Inches(5.65), Inches(5.8), Inches(1.2),
        "That last point is the finding, not a bug. Liquid large-caps are crowded. The data system is still the right foundation.",
        size=13, color=MUTED)
    _footer(s, 2, total)

    # —— 3 Architecture ——
    s = _blank(prs)
    _header(s, "DATA LAYER  ·  STORAGE", "How history is stored — and why the schema looks like this",
            "A pairs engine will query thousands of days for many tickers. The unit of storage is therefore a daily bar, "
            "keyed so that ingest, API, and research all agree on the same row.")
    labels = [
        ("Yahoo", "OHLCV + adj close\n.SS tickers"),
        ("Ingest", "bootstrap / update\nbatched, resumable"),
        ("MongoDB", "daily_bars +\ninstruments"),
        ("REST", "GET /v1/\ntimeseries"),
        ("Research", "corr, clusters,\nbacktest"),
    ]
    for i, (title, sub) in enumerate(labels):
        left = Inches(0.35 + i * 2.58)
        navy = i in (2, 3)
        _box(s, left, Inches(1.6), Inches(2.4), Inches(1.45), NAVY if navy else WHITE, None if navy else LINE)
        tc, sc = (WHITE, SOFT) if navy else (NAVY, MUTED)
        _tb(s, left, Inches(1.68), Inches(2.4), Inches(0.35), title, size=14, bold=True, color=tc, align=PP_ALIGN.CENTER)
        _tb(s, left, Inches(2.05), Inches(2.4), Inches(0.9), sub, size=12, color=sc, align=PP_ALIGN.CENTER)
        if i < 4:
            _tb(s, left + Inches(2.22), Inches(2.05), Inches(0.35), Inches(0.4), "→", size=18, bold=True, color=GOLD, align=PP_ALIGN.CENTER)
    _table(
        s, Inches(0.35), Inches(3.2), Inches(8.35), Inches(3.85),
        ["Collection", "What one document is", "Why"],
        [
            ["daily_bars", "Ticker + date + OHLCV + adj_close", "Unique index → upserts; research reads adj_close"],
            ["instruments", "SSE code, name, share class", "Universe for bootstrap; later: sector tags"],
            ["ingest_state", "Last good date per ticker", "Resume after a crash without re-downloading 2010"],
            ["ingest_runs", "One job log (ok / empty / failed)", "You can see if last night’s cron actually ran"],
        ],
        col_w=[Inches(1.9), Inches(3.15), Inches(3.3)],
        size=11,
    )
    _box(s, Inches(8.85), Inches(3.2), Inches(4.1), Inches(3.85), WHITE, LINE)
    _tb(s, Inches(9.0), Inches(3.32), Inches(3.8), Inches(0.32), "One daily_bars document", size=14, bold=True, color=NAVY)
    _tb(s, Inches(9.0), Inches(3.68), Inches(3.8), Inches(3.15),
        '{\n  "ticker": "600000.SS",\n  "date": "2010-01-04",\n'
        '  "open": 9.02, "high": 9.05,\n  "low": 8.76, "close": 8.80,\n'
        '  "adj_close": 8.12,\n  "volume": 159964606,\n  "source": "yahoo"\n}',
        size=12, color=INK, font="Consolas")
    _footer(s, 3, total)

    # —— 4 API ——
    s = _blank(prs)
    _header(s, "DATA LAYER  ·  API", "The required endpoint: slice a ticker by date and fields",
            "The brief is a query contract, not a GUI. Anyone (you, a notebook, next week’s code) should be able to pull "
            "exactly the columns they need without downloading the whole database.")
    _box(s, Inches(0.35), Inches(1.6), Inches(12.63), Inches(1.05), NAVY)
    _tb(s, Inches(0.5), Inches(1.68), Inches(12.3), Inches(0.28), "GET /v1/timeseries", size=12, bold=True, color=GOLD, font="Consolas")
    _tb(s, Inches(0.5), Inches(1.98), Inches(12.3), Inches(0.5),
        "?ticker=600000&start=2010-01-01&end=2010-01-15&fields=high,low,volume",
        size=16, color=WHITE, font="Consolas")
    _box(s, Inches(0.35), Inches(2.8), Inches(6.25), Inches(4.25), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(2.92), Inches(6.0), Inches(0.32), "What the parameters mean", size=15, bold=True, color=NAVY)
    _plist(s, Inches(0.5), Inches(3.3), Inches(5.95), Inches(3.55), [
        "ticker — 600000, 600000.SS or sh600000 all become 600000.SS (Yahoo SSE form).",
        "start / end — inclusive calendar dates. Non-trading days simply have no row.",
        "fields — comma list from open, high, low, close, adj_close, volume. Unknown names → HTTP 400.",
        "date is always returned, even if you did not ask for it, so the series is usable.",
        "Omit fields and you get the full bar. Task 2 only asks for adj_close.",
        "Swagger UI lives at /docs so a reviewer can try the contract without curl.",
    ], size=13, gap=7)
    _box(s, Inches(6.75), Inches(2.8), Inches(6.23), Inches(4.25), WHITE, LINE)
    _tb(s, Inches(6.9), Inches(2.92), Inches(5.95), Inches(0.32), "Response (trimmed)", size=15, bold=True, color=NAVY)
    _tb(s, Inches(6.9), Inches(3.3), Inches(5.95), Inches(3.55),
        '{\n  "ticker": "600000.SS",\n  "start": "2010-01-01",\n  "end": "2010-01-15",\n'
        '  "fields": ["high", "low", "volume"],\n  "count": 10,\n  "data": [\n'
        '    {"date": "2010-01-04",\n     "high": 9.05, "low": 8.76,\n     "volume": 159964606}\n  ]\n}',
        size=13, color=INK, font="Consolas")
    _footer(s, 4, total)

    # —— 5 Updater ——
    s = _blank(prs)
    _header(s, "DATA LAYER  ·  UPDATER", "One script, two modes: full history, then every new session",
            "Yahoo rate-limits. A 16-year load of many names will fail halfway if you do not checkpoint. "
            "The updater therefore stores the last date per ticker and always continues from there.")
    _box(s, Inches(0.35), Inches(1.6), Inches(6.25), Inches(2.55), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.72), Inches(6.0), Inches(0.3), "sse-data bootstrap", size=16, bold=True, color=NAVY, font="Consolas")
    _plist(s, Inches(0.5), Inches(2.1), Inches(5.95), Inches(1.85), [
        "Pulls (or resumes) daily bars from 2010-01-01 to today.",
        "If 600000 already has data through 2018, the next run starts on 2019-01-01.",
        "Use --tickers for a smoke test; omit it for the full SSE A + STAR list.",
    ], size=13, gap=6)
    _box(s, Inches(6.75), Inches(1.6), Inches(6.23), Inches(2.55), WHITE, LINE)
    _tb(s, Inches(6.9), Inches(1.72), Inches(5.95), Inches(0.3), "sse-data update", size=16, bold=True, color=NAVY, font="Consolas")
    _plist(s, Inches(6.9), Inches(2.1), Inches(5.95), Inches(1.85), [
        "Same code path, smaller window: last stored date + 1 → today.",
        "Meant for cron after the A-share close, e.g. 18:30 China time, weekdays.",
        "Writes an ingest_runs document so you can see last night’s counts.",
    ], size=13, gap=6)
    _table(
        s, Inches(0.35), Inches(4.3), Inches(12.63), Inches(2.75),
        ["Decision", "Choice", "Short explanation"],
        [
            ["Price source", "Yahoo Finance (.SS)", "Named in the brief. We keep unadjusted OHLC and adj_close."],
            ["Name list", "East Money SSE A + STAR", "Yahoo does not publish a stable “all SSE stocks” file."],
            ["Writes", "Bulk upsert on (ticker, date)", "Re-running a day repairs holes; it never creates twins."],
            ["Pace", "15 names, then 2s pause", "Keeps Yahoo from 429-ing a 2,000-name bootstrap."],
        ],
        col_w=[Inches(2.1), Inches(3.5), Inches(7.03)],
        size=12,
    )
    _footer(s, 5, total)

    # —— 6 Correlation ——
    s = _blank(prs)
    _header(s, "A  ·  CORRELATION", "Three formulas: return → correlation → distance",
            "Step through them in order. We never cluster on raw prices (a ¥1,800 stock and a ¥8 stock are not comparable). "
            "We cluster on how their daily percentage moves co-vary.")
    _box(s, Inches(0.35), Inches(1.58), Inches(12.63), Inches(1.55), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.64), Inches(12.35), Inches(1.4),
        "(1)  rᵢ,ₜ = ln(Pᵢ,ₜ / Pᵢ,ₜ₋₁)     log return of stock i on day t.  Example: 10.00 → 10.20  ⇒  r = ln(1.02) ≈ +1.98%.\n"
        "(2)  ρᵢⱼ = Corr(rᵢ, rⱼ)           Pearson correlation over T = 252 overlapping days.  ρ = 1 lockstep, 0 unrelated, −1 opposite.\n"
        "(3)  dᵢⱼ = √ 2(1 − ρᵢⱼ)           Mantegna distance.  Clustering needs a distance, not a correlation.  ρ = 1 ⇒ d = 0;  ρ = 0 ⇒ d ≈ 1.41.",
        size=14, color=NAVY)
    _table(
        s, Inches(0.35), Inches(3.25), Inches(7.45), Inches(3.8),
        ["Symbol", "Meaning", "Why it is here"],
        [
            ["Pᵢ,ₜ", "Adj. close of i on day t", "Splits/dividends already in the price"],
            ["rᵢ,ₜ", "One-day log return", "Additive; comparable across price levels"],
            ["ρᵢⱼ", "How often i and j move together", "Grouping feature — not a trade"],
            ["dᵢⱼ", "How far i is from j in return space", "Input to hierarchical clustering"],
            ["T = 252", "One trading year of days", "Stable ρ; not so long it mixes regimes"],
        ],
        col_w=[Inches(1.35), Inches(2.7), Inches(3.4)],
        size=11,
    )
    _box(s, Inches(7.95), Inches(3.25), Inches(5.03), Inches(3.8), WHITE, LINE)
    _tb(s, Inches(8.1), Inches(3.35), Inches(4.75), Inches(0.3), "Worked numbers (last formation)", size=13, bold=True, color=GOLD)
    example_lines = [
        "Ping An vs CPIC:  ρ = 0.84",
        "d = √ 2(1 − 0.84) = √ 0.32 ≈ 0.57",
        "Close in distance → same cluster (insurers).",
        "",
        "If instead ρ = 0.10,  d ≈ 1.34.",
        "Far apart → different clusters, no pair.",
        "",
        "Rule of thumb we use later: only",
        "search for pairs if |ρ| ≥ 0.50.",
    ]
    _plist(s, Inches(8.1), Inches(3.7), Inches(4.75), Inches(3.2), [ln for ln in example_lines if ln], size=12, gap=4)
    _footer(s, 6, total)

    # —— 7 Clustering ——
    s = _blank(prs)
    _header(s, "B  ·  CLUSTERING", "Average-linkage clustering on dᵢⱼ, then cut into k groups",
            "Think of stocks as points. Distance between two points is dᵢⱼ from the last slide. We keep merging the two closest groups until k groups remain. "
            f"k is not guessed: we try 3…8 and keep the cut with the best silhouette. Last window: k = {clusters.get('k')}, silhouette = {clusters.get('silhouette')}.")
    _box(s, Inches(0.35), Inches(1.58), Inches(12.63), Inches(1.7), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.64), Inches(12.35), Inches(1.52),
        "(4)  D(A,B) = (1 / |A||B|)  Σᵢ∈A Σⱼ∈B dᵢⱼ     average linkage: distance between two groups = mean of all cross-pair distances.\n"
        "      Why average, not single linkage? Single linkage chains (A near B, B near C ⇒ A–C merge even if A is far from C). Average is stabler for stocks.\n"
        "(5)  Silhouette of a name = (b − a) / max(a, b).  a = mean d to others in its cluster;  b = mean d to the nearest other cluster.\n"
        "      Near 1 = tight, well separated.  Near 0 = overlapping.  0.19 is typical for equities — groups exist, but they are not islands.",
        size=13, color=NAVY)
    cluster_rows = []
    for g in sorted(groups, key=lambda x: -x.get("size", 0)):
        cluster_rows.append([
            str(g.get("id")),
            _theme(g.get("tickers") or []),
            str(g.get("size")),
            _names(g.get("tickers") or [], limit=8),
        ])
    _table(
        s, Inches(0.35), Inches(3.4), Inches(12.63), Inches(3.65),
        ["#", "Theme this d-matrix recovered", "n", "Members — we only form pairs inside a row"],
        cluster_rows[:6],
        col_w=[Inches(0.55), Inches(2.7), Inches(0.55), Inches(8.83)],
        size=11,
    )
    _footer(s, 7, total)

    # —— 8 Pair filter ——
    s = _blank(prs)
    _header(s, "C  ·  PAIR SELECTION", "From a cluster, keep only a hedge whose residual mean-reverts",
            "Correlation said they move together. Cointegration asks a harder question: is there a stable linear combination of the two log prices? "
            "If yes, the leftover (the spread) is the thing we trade. If no, fading the gap is fading a random walk.")
    _box(s, Inches(0.35), Inches(1.58), Inches(12.63), Inches(1.85), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.64), Inches(12.35), Inches(1.7),
        "(6)  ln P_Y,ₜ = α + β ln P_X,ₜ + εₜ      OLS: explain log Y with log X.  β̂ = hedge ratio (units of X per 1 unit of Y).\n"
        "(7)  sₜ = ln P_Y,ₜ − α̂ − β̂ ln P_X,ₜ     spread = leftover after the hedge.  If cointegrated, sₜ wanders around 0, not off to infinity.\n"
        "(8)  Δsₜ = λ sₜ₋₁ + uₜ                   regress today’s change in s on yesterday’s level.  Mean reversion needs λ < 0.\n"
        "      HL = ln(2) / |λ|                    half-life: days for a shock to s to shrink by 50%.  Example: λ = −0.076 ⇒ HL ≈ 9 days.",
        size=13, color=NAVY)
    _table(
        s, Inches(0.35), Inches(3.55), Inches(12.63), Inches(3.5),
        ["Symbol / test", "Plain meaning", "Keep the pair only if"],
        [
            ["Y, X", "The two legs, both in the same cluster", "Already passed the correlation screen"],
            ["α̂, β̂", "Intercept and slope of the log-log hedge", "0.2 ≤ β̂ ≤ 3  (else it is not a long–short)"],
            ["sₜ", "How rich/cheap Y is vs that hedge", "We will trade this, not the two prices"],
            ["EG p-value", "ADF-style test that sₜ is stationary", "p < 0.05  (otherwise sₜ is a random walk)"],
            ["λ, HL", "Speed of pull-back; holding-period scale", "λ < 0 and  5 ≤ HL ≤ 90 trading days"],
        ],
        col_w=[Inches(2.15), Inches(5.2), Inches(5.28)],
        size=11,
    )
    _footer(s, 8, total)

    # —— 9 Trading rules ——
    s = _blank(prs)
    _header(s, "C  ·  SIGNALS AND P&L", "Turn the spread into a z-score, then into a position and a daily return",
            "β̂ is frozen from formation — we do not refit it on the days we trade. The z-score is rolling so a slow drift in the level of s is not "
            "treated as a 4.5σ event. Execution is next day’s close: no look-ahead, and consistent with A-share T+1.")
    _box(s, Inches(0.35), Inches(1.58), Inches(12.63), Inches(2.05), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.64), Inches(12.35), Inches(1.9),
        "(9)   zₜ = (sₜ − μₜ,₆₀) / σₜ,₆₀     μ, σ = mean and stdev of s over the last 60 days.  z is “how many sigmas is the spread from its recent mean?”\n"
        "       z = +2.3  →  Y is 2.3σ expensive vs X  →  short the spread (short Y, long β X).   z = −2.3  →  the opposite.\n"
        "(10)  posₜ ∈ {−1, 0, +1}            −1 = short spread, +1 = long spread.  Signal at close t; position actually changes at close t+1.\n"
        "(11)  Rₜ ≈ posₜ₋₁ (r_Y,ₜ − β̂ r_X,ₜ)  dollar-neutral P&L: you earn Y’s return, minus β times X’s return, times yesterday’s sign.\n"
        "       Costs (~21 bps) are subtracted when pos changes, not every day.",
        size=13, color=NAVY)
    _table(
        s, Inches(0.35), Inches(3.75), Inches(6.25), Inches(3.3),
        ["If z is…", "We do", "Until"],
        [
            ["≥ +2", "Short spread (Y rich)", "|z| ≤ 0.5  (gap closed)"],
            ["≤ −2", "Long spread (Y cheap)", "|z| ≤ 0.5"],
            ["|z| ≥ 4.5", "Stop — relation broke", "Flatten immediately"],
            ["held 30 days", "Time stop", "Do not marry the trade"],
            ["signal today", "Fill tomorrow’s close", "T+1 / no look-ahead"],
        ],
        col_w=[Inches(1.7), Inches(2.25), Inches(2.3)],
        size=11,
    )
    _table(
        s, Inches(6.75), Inches(3.75), Inches(6.23), Inches(3.3),
        ["Cost piece", "Level", "Hits when"],
        [
            ["Commission", "3 bps / side", "Every fill"],
            ["Slippage", "5 bps / side", "Every fill"],
            ["Stamp duty", "5 bps", "Sells only"],
            ["Open or close pair", "~21 bps of one leg", "pos changes"],
            ["Borrow fee", "Not in the P&L", "See caveats"],
        ],
        col_w=[Inches(2.15), Inches(2.05), Inches(2.03)],
        size=11,
    )
    _footer(s, 9, total)

    # —— 10 Backtest design ——
    s = _blank(prs)
    _header(s, "D  ·  BACKTEST DESIGN", "Estimate on one window, trade the next, then roll — never fit on the test days",
            "A single in-sample pair list over 2010–2026 would overstate the edge. Walk-forward rebuilds clusters and hedges every quarter-sized trade window.")
    boxes = [
        ("Formation 252d", "Correlate, cluster,\npick pairs, freeze β"),
        ("Trade 63d", "Signals and P&L\nwith frozen hedge"),
        ("Roll +63d", "New formation ends\nwhere the last trade ended"),
        ("Repeat", f"{m.get('n_windows', '—')} windows\n{n_names} names"),
    ]
    for i, (title, sub) in enumerate(boxes):
        left = Inches(0.35 + i * 3.25)
        _box(s, left, Inches(1.6), Inches(3.1), Inches(1.55), NAVY if i == 3 else WHITE, None if i == 3 else LINE)
        tc, sc = (WHITE, SOFT) if i == 3 else (NAVY, MUTED)
        _tb(s, left + Inches(0.1), Inches(1.7), Inches(2.9), Inches(0.4), title, size=14, bold=True, color=tc, align=PP_ALIGN.CENTER)
        _tb(s, left + Inches(0.1), Inches(2.15), Inches(2.9), Inches(0.85), sub, size=12, color=sc, align=PP_ALIGN.CENTER)
        if i < 3:
            _tb(s, left + Inches(2.95), Inches(2.05), Inches(0.3), Inches(0.4), "→", size=16, bold=True, color=GOLD)
    _table(
        s, Inches(0.35), Inches(3.35), Inches(12.63), Inches(3.7),
        ["Choice", "Setting", "Why"],
        [
            ["Universe", f"{n_names} liquid SSE names, not the full 2,000", "Yahoo coverage + we can inspect every cluster"],
            ["Sample", sample, "After a 252-day warm-up from 2015"],
            ["Portfolio", "Equal-weight pairs; idle day = 0", "Does not pretend unused capital is in T-bills"],
            ["Costs", "3 / 5 / 5 bps comm / slip / stamp", "Stylised but not zero — mega-cap edge is thin"],
            ["Look-ahead", "None. β from formation; fill t+1", "Matches T+1 and a next-bar execution assumption"],
        ],
        col_w=[Inches(2.0), Inches(4.4), Inches(6.23)],
        size=12,
    )
    _footer(s, 10, total)

    # —— 11 Results ——
    s = _blank(prs)
    _header(s, "D  ·  RESULTS, NET OF COSTS", "Clusters recovered real industries. The residual trade did not pay for itself on mega-caps.",
            "Read this as a research outcome: the pipeline works; this universe is too efficient after costs. That is useful for the next task.")
    kpis = [
        (f"{m.get('sharpe', 0):+.2f}", "Sharpe, annualised", "Below 0 after costs"),
        (f"{100 * float(m.get('cagr') or 0):+.1f}%", "CAGR", "Start capital = 1.0"),
        (f"{100 * float(m.get('max_drawdown') or 0):.1f}%", "Max drawdown", "Peak to trough, net"),
        (f"{m.get('n_trades', '—')}", "Round-trips", f"{m.get('avg_hold_days', '—')}d avg hold · {m.get('stop_exits', 0)} stops"),
    ]
    for i, (val, lab, note) in enumerate(kpis):
        left = Inches(0.35 + i * 3.25)
        _box(s, left, Inches(1.6), Inches(3.1), Inches(1.35), WHITE, LINE)
        _tb(s, left, Inches(1.66), Inches(3.1), Inches(0.55), val, size=22, bold=True, color=RED, align=PP_ALIGN.CENTER)
        _tb(s, left, Inches(2.18), Inches(3.1), Inches(0.3), lab, size=12, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        _tb(s, left, Inches(2.46), Inches(3.1), Inches(0.35), note, size=11, color=MUTED, align=PP_ALIGN.CENTER)
    if years:
        chart_data = CategoryChartData()
        chart_data.categories = eq_cats
        chart_data.add_series("Net equity (start = 1)", eq_vals)
        chart = s.shapes.add_chart(
            XL_CHART_TYPE.LINE, Inches(0.25), Inches(3.05), Inches(8.3), Inches(4.05), chart_data
        ).chart
        chart.has_legend = False
        try:
            chart.series[0].format.line.color.rgb = ACCENT
            chart.series[0].format.line.width = Pt(2.0)
        except Exception:
            pass
    _box(s, Inches(8.55), Inches(3.1), Inches(4.4), Inches(3.95), WHITE, LINE)
    _tb(s, Inches(8.7), Inches(3.22), Inches(4.15), Inches(0.32), "How to read the curve", size=14, bold=True, color=NAVY)
    _plist(s, Inches(8.7), Inches(3.6), Inches(4.15), Inches(3.25), [
        "Y-axis is net equity, start = 1. A finish below 1 means costs + residual noise won.",
        "Stops were rare (3 of 137). We were not blown up by 4.5σ events; we were nickeled by turnover.",
        "2017 and 2021 are the weak years — crowded quality / liquor / bank pairs de-rated together.",
        "Takeaway for next week: same API, harder universe (mid-caps), or a borrow-aware rule.",
    ], size=12, gap=8)
    _footer(s, 11, total)

    # —— 12 Caveats ——
    s = _blank(prs)
    _header(s, "LIMITS AND NEXT STEP", "What this backtest does not claim — and what we would change without touching MongoDB",
            "Honesty here is part of the methodology. A-share microstructure is not US equity microstructure.")
    _box(s, Inches(0.35), Inches(1.6), Inches(6.25), Inches(5.45), WHITE, LINE)
    _tb(s, Inches(0.5), Inches(1.72), Inches(5.95), Inches(0.32), "Caveats  (do not hide these)", size=15, bold=True, color=NAVY)
    _plist(s, Inches(0.5), Inches(2.15), Inches(5.95), Inches(4.65), [
        "Shorting: 融资融券 is limited and often expensive. We assume the short leg is available at 5 bps slippage. Live trading needs a borrow screen or a long-only spread.",
        "Limits: main board ±10% can gap the spread through the stop; STAR is ±20%.",
        "Vendor: Yahoo adj_close can disagree with Wind / Tushare on a handful of corporate actions.",
        "Costs: 3/5/5 bps is stylised. Institutional commissions are lower; borrow is extra.",
        "Search: walk-forward stops us fitting β on trade days. It does not stop us choosing z = 2 after seeing results.",
    ], size=13, gap=8)
    _box(s, Inches(6.75), Inches(1.6), Inches(6.23), Inches(5.45), WHITE, LINE)
    _tb(s, Inches(6.9), Inches(1.72), Inches(5.95), Inches(0.32), "Keep the data system. Change the book.", size=15, bold=True, color=NAVY)
    _plist(s, Inches(6.9), Inches(2.15), Inches(5.95), Inches(4.65), [
        "Do not rebuild MongoDB or /v1/timeseries. That was the point of this week.",
        "Point research at mid-caps / less crowded SSE names — the brief said the edge is larger where competition is thinner.",
        "Store industry on instruments and compare GICS clusters with correlation clusters.",
        "Add a borrow flag before claiming a live long–short P&L.",
        "The 3 stop-outs vs 137 trades say the stop is not the problem. Capacity and costs are.",
    ], size=13, gap=8)
    _footer(s, 12, total)

    # —— 13 Appendix ——
    s = _blank(prs)
    _header(s, "APPENDIX", "How a reviewer runs it — same artefacts next week",
            "Commands assume MongoDB on 127.0.0.1:27017 and the project venv. Full formulas: docs/TASK2_METHODS.md.")
    _box(s, Inches(0.35), Inches(1.6), Inches(12.63), Inches(2.35), NAVY)
    _tb(s, Inches(0.5), Inches(1.72), Inches(12.35), Inches(2.05),
        "sse-data bootstrap --tickers 600000,600519,…     # history since 2010 (resume-safe)\n"
        "sse-data update                                   # last date → today   (cron this)\n"
        "sse-data serve                                    # API  :8000/docs  and  /v1/timeseries\n"
        "sse-data research                                 # cluster + walk-forward → JSON + this deck",
        size=15, color=WHITE, font="Consolas")
    _table(
        s, Inches(0.35), Inches(4.1), Inches(12.63), Inches(2.95),
        ["Artefact", "Path", "What to extend later"],
        [
            ["This deck", "docs/SSE_StatArb_Slides.pptx", "Keep as the methods narrative"],
            ["Formulas", "docs/TASK2_METHODS.md", "A/B/C with full equations"],
            ["Numbers", "data/research/task2_results.json", "Swap universe, rerun research"],
            ["API / DB", "src/sse_data/  ·  Mongo sse_market", "Add fields, not new databases"],
        ],
        col_w=[Inches(2.1), Inches(4.3), Inches(6.23)],
        size=12,
    )
    _footer(s, 13, total)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(OUT)
    prs.save(ALT)
    print(f"wrote {OUT}")
    print(f"wrote {ALT}")


def main() -> None:
    if not RESULTS.exists():
        raise SystemExit(f"missing {RESULTS} — run: sse-data research")
    build(json.loads(RESULTS.read_text(encoding="utf-8")))


if __name__ == "__main__":
    main()

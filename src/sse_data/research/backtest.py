from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from sse_data.research.clustering import cluster_from_prices
from sse_data.research.correlation import top_correlated_pairs
from sse_data.research.pairs import select_pairs
from sse_data.research.prices import aligned_log_prices
from sse_data.research.strategy import StrategyConfig, pair_pnl_series


def _sharpe(returns: pd.Series, periods: int = 252) -> float:
    mu = float(returns.mean())
    sd = float(returns.std(ddof=1))
    if sd == 0 or np.isnan(sd):
        return 0.0
    return (mu / sd) * np.sqrt(periods)


def _max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min()) if len(dd) else 0.0


def _cagr(equity: pd.Series) -> float:
    if len(equity) < 2:
        return 0.0
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0 or end <= 0:
        return 0.0
    days = (equity.index[-1] - equity.index[0]).days
    if days <= 0:
        return 0.0
    return float((end / start) ** (365.25 / days) - 1.0)


def walk_forward(
    prices: pd.DataFrame,
    *,
    formation_days: int = 252,
    trade_days: int = 63,
    cfg: StrategyConfig | None = None,
    start: date | None = None,
    end: date | None = None,
) -> dict[str, Any]:
    """Rolling formation / trading backtest.

    Formation window estimates correlation, clusters, hedge ratios and z-score
    moments. The following `trade_days` are traded with those frozen parameters.
    """
    cfg = cfg or StrategyConfig()
    panel = aligned_log_prices(prices, min_obs=formation_days)
    if start:
        panel = panel[panel.index >= pd.Timestamp(start)]
    if end:
        panel = panel[panel.index <= pd.Timestamp(end)]
    dates = list(panel.index)
    if len(dates) < formation_days + trade_days:
        raise ValueError("not enough history for walk-forward windows")

    all_returns: list[pd.Series] = []
    all_trades: list[dict] = []
    windows: list[dict] = []
    last_corr_snapshot = None
    last_cluster_snapshot = None

    i = 0
    while i + formation_days + 20 <= len(dates):
        form_idx = dates[i : i + formation_days]
        trade_idx = dates[i + formation_days : i + formation_days + trade_days]
        if len(trade_idx) < 20:
            break
        form = panel.loc[form_idx].dropna(axis=1, thresh=int(formation_days * 0.85))
        if form.shape[1] < 6:
            i += trade_days
            continue
        clustered = cluster_from_prices(form)
        pairs = select_pairs(form, clustered["groups"], clustered["corr"])
        last_corr_snapshot = clustered["corr"]
        last_cluster_snapshot = {k: v for k, v in clustered.items() if k != "corr"}
        window_px = panel.loc[form_idx[0] : trade_idx[-1]]
        window_rets = []
        for pair in pairs:
            pnl, trades = pair_pnl_series(window_px, pair, cfg, trade_start=trade_idx[0])
            window_rets.append(pnl)
            all_trades.extend(trades)
        if window_rets:
            combined = pd.concat(window_rets, axis=1).mean(axis=1)
            all_returns.append(combined)
        windows.append(
            {
                "formation_start": str(form_idx[0]),
                "formation_end": str(form_idx[-1]),
                "trade_start": str(trade_idx[0]),
                "trade_end": str(trade_idx[-1]),
                "n_pairs": len(pairs),
                "pairs": [p.to_dict() for p in pairs],
            }
        )
        i += trade_days

    if not all_returns:
        raise RuntimeError("no tradable pairs found in any window — relax filters or add names")

    daily = pd.concat(all_returns).groupby(level=0).mean().sort_index()
    full_index = panel.loc[daily.index.min() : daily.index.max()].index
    daily = daily.reindex(full_index).fillna(0.0)
    equity = (1.0 + daily).cumprod()
    hit = [t for t in all_trades if "hold_days" in t]
    # We did not store trade PnL per round; hit rate uses closed trades count only.
    metrics = {
        "n_windows": len(windows),
        "n_trades": len(all_trades),
        "avg_hold_days": round(float(np.mean([t["hold_days"] for t in all_trades])), 2) if all_trades else 0.0,
        "stop_exits": int(sum(1 for t in all_trades if t.get("stop"))),
        "total_return": round(float(equity.iloc[-1] - 1.0), 4),
        "cagr": round(_cagr(equity), 4),
        "sharpe": round(_sharpe(daily.dropna()), 3),
        "max_drawdown": round(_max_drawdown(equity), 4),
        "hit_placeholder": len(hit),
    }
    monthly = equity.resample("ME").last().pct_change().dropna() if hasattr(equity, "resample") else pd.Series(dtype=float)
    top_pairs = top_correlated_pairs(last_corr_snapshot, n=12, min_abs=0.3) if last_corr_snapshot is not None else []

    def _eq_points(series: pd.Series, freq: str = "ME") -> list[dict]:
        sampled = series.resample(freq).last().dropna()
        return [{"date": str(idx.date()) if hasattr(idx, "date") else str(idx), "equity": round(float(val), 4)} for idx, val in sampled.items()]

    return {
        "config": {
            "formation_days": formation_days,
            "trade_days": trade_days,
            "entry_z": cfg.entry_z,
            "exit_z": cfg.exit_z,
            "stop_z": cfg.stop_z,
            "z_window": cfg.z_window,
            "max_hold": cfg.max_hold,
            "commission": cfg.commission,
            "stamp_duty": cfg.stamp_duty,
            "slippage": cfg.slippage,
        },
        "metrics": metrics,
        "clusters": last_cluster_snapshot,
        "top_correlations": top_pairs,
        "windows": windows,
        "equity_monthly": _eq_points(equity),
        "equity_start": str(equity.index[0]),
        "equity_end": str(equity.index[-1]),
        "n_names": int(panel.shape[1]),
        "tickers": list(panel.columns),
    }

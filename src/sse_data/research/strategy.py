from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from sse_data.research.pairs import PairCandidate


@dataclass
class StrategyConfig:
    entry_z: float = 2.0
    exit_z: float = 0.5
    stop_z: float = 4.5
    z_window: int = 60
    max_hold: int = 30
    commission: float = 0.0003
    stamp_duty: float = 0.0005
    slippage: float = 0.0005


def _leg_cost(cfg: StrategyConfig, is_sell: bool) -> float:
    cost = cfg.commission + cfg.slippage
    if is_sell:
        cost += cfg.stamp_duty
    return cost


def round_trip_cost(cfg: StrategyConfig) -> float:
    """Cost of opening or closing a dollar-neutral pair, as a fraction of one-leg capital."""
    return _leg_cost(cfg, is_sell=False) + _leg_cost(cfg, is_sell=True)


def pair_pnl_series(
    prices: pd.DataFrame,
    pair: PairCandidate,
    cfg: StrategyConfig,
    *,
    trade_start=None,
) -> tuple[pd.Series, list[dict]]:
    """Trade a formation-calibrated hedge with a rolling z-score.

    β, α are frozen from formation. μ and σ of the spread are rolling so a
    slow mean shift does not immediately trip the stop. Signal at close t,
    fill at close t+1 (no look-ahead; compatible with T+1).
    """
    cols = prices[[pair.y, pair.x]].dropna()
    log_p = np.log(cols.where(cols > 0))
    spread = log_p[pair.y] - pair.intercept - pair.beta * log_p[pair.x]
    min_p = max(20, cfg.z_window // 2)
    z = (spread - spread.rolling(cfg.z_window, min_periods=min_p).mean()) / spread.rolling(
        cfg.z_window, min_periods=min_p
    ).std(ddof=1)
    r_y = np.log(cols[pair.y]).diff()
    r_x = np.log(cols[pair.x]).diff()
    spread_ret = r_y - pair.beta * r_x

    start_ts = pd.Timestamp(trade_start) if trade_start is not None else None
    dates = list(cols.index)
    position = 0
    pending: int | None = None
    hold_days = 0
    trades: list[dict] = []
    daily = []
    cost = round_trip_cost(cfg)

    for i, dt in enumerate(dates):
        ts = pd.Timestamp(dt)
        live = start_ts is None or ts >= start_ts
        realized = 0.0
        if live and i > 0 and position != 0:
            realized += position * float(spread_ret.iloc[i])
        if live and i > 0 and pending is not None:
            realized -= cost
            position = pending
            pending = None
            hold_days = 0
        if position != 0:
            hold_days += 1

        z_t = float(z.iloc[i])
        last = i == len(dates) - 1
        if (not live) or np.isnan(z_t):
            daily.append((dt, realized))
            continue

        want = position
        if position == 0:
            if z_t >= cfg.entry_z:
                want = -1
            elif z_t <= -cfg.entry_z:
                want = 1
        else:
            timed_out = hold_days >= cfg.max_hold
            if abs(z_t) <= cfg.exit_z or abs(z_t) >= cfg.stop_z or timed_out:
                want = 0

        stopped = abs(z_t) >= cfg.stop_z
        if last:
            if position != 0:
                realized -= cost
                trades.append(
                    {
                        "pair": f"{pair.y}/{pair.x}",
                        "exit_date": str(ts.date()),
                        "hold_days": hold_days,
                        "exit_z": round(z_t, 3),
                        "stop": stopped,
                    }
                )
                position = 0
            pending = None
        elif want != position and pending is None:
            pending = want
            if position != 0:
                trades.append(
                    {
                        "pair": f"{pair.y}/{pair.x}",
                        "exit_date": str(ts.date()),
                        "hold_days": hold_days,
                        "exit_z": round(z_t, 3),
                        "stop": stopped,
                    }
                )
        daily.append((dt, realized))

    series = pd.Series({dt: val for dt, val in daily}).sort_index()
    if start_ts is not None:
        series = series[series.index >= start_ts]
    return series, trades

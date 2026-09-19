import numpy as np
import pandas as pd

from sse_data.research.correlation import correlation_distance, correlation_matrix
from sse_data.research.pairs import PairCandidate, half_life
from sse_data.research.strategy import StrategyConfig, pair_pnl_series


def test_identical_series_have_unit_correlation():
    idx = pd.date_range("2015-01-01", periods=80, freq="B")
    rng = np.random.default_rng(0)
    px = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 80)))
    prices = pd.DataFrame({"AAA.SS": px, "BBB.SS": px * 1.1}, index=idx)
    corr = correlation_matrix(prices)
    assert corr.loc["AAA.SS", "BBB.SS"] > 0.999
    dist = correlation_distance(corr)
    assert dist.loc["AAA.SS", "BBB.SS"] < 0.05


def test_ou_half_life_recovers_scale():
    rng = np.random.default_rng(1)
    target_hl = 20.0
    lam = -np.log(2.0) / target_hl
    values = [0.0]
    for _ in range(1200):
        values.append(values[-1] + lam * values[-1] + rng.normal(0, 0.05))
    hl = half_life(pd.Series(values))
    assert 8 < hl < 45


def test_zscore_enters_when_spread_is_wide():
    idx = pd.date_range("2020-01-01", periods=40, freq="B")
    x = pd.Series(np.linspace(10, 12, 40), index=idx)
    y = x.copy()
    y.iloc[10:16] = y.iloc[10:16] * 1.15
    prices = pd.DataFrame({"Y.SS": y, "X.SS": x})
    pair = PairCandidate(
        y="Y.SS",
        x="X.SS",
        cluster_id=1,
        rho=0.9,
        beta=1.0,
        intercept=0.0,
        coint_pvalue=0.01,
        half_life=10.0,
        spread_mean=0.0,
        spread_std=0.02,
    )
    pnl, trades = pair_pnl_series(prices, pair, StrategyConfig(entry_z=2.0, exit_z=0.5, stop_z=8.0))
    assert len(pnl) == 40
    assert isinstance(trades, list)

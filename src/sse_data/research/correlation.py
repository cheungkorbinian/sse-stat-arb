from __future__ import annotations

import numpy as np
import pandas as pd

from sse_data.research.prices import log_returns


def correlation_matrix(prices: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of daily log returns.

    ρ_ij = Corr(r_i, r_j),  r_{i,t} = ln(P_{i,t} / P_{i,t-1})
    """
    rets = log_returns(prices).dropna(how="all")
    corr = rets.corr(method="pearson")
    return corr.clip(-1.0, 1.0)


def correlation_distance(corr: pd.DataFrame) -> pd.DataFrame:
    """Mantegna distance d_ij = sqrt(2 (1 - ρ_ij))."""
    arr = np.sqrt(np.maximum(0.0, 2.0 * (1.0 - corr.to_numpy(dtype=float))))
    arr = np.array(arr, copy=True)
    np.fill_diagonal(arr, 0.0)
    return pd.DataFrame(arr, index=corr.index, columns=corr.columns)


def top_correlated_pairs(corr: pd.DataFrame, n: int = 15, min_abs: float = 0.0) -> list[dict]:
    pairs = []
    tickers = list(corr.columns)
    for i, a in enumerate(tickers):
        for b in tickers[i + 1 :]:
            rho = float(corr.loc[a, b])
            if np.isnan(rho) or abs(rho) < min_abs:
                continue
            pairs.append({"y": a, "x": b, "rho": rho})
    pairs.sort(key=lambda item: abs(item["rho"]), reverse=True)
    return pairs[:n]

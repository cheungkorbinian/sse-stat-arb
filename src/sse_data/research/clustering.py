from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.metrics import silhouette_score

from sse_data.research.correlation import correlation_distance, correlation_matrix


def _condensed(dist: pd.DataFrame) -> np.ndarray:
    matrix = dist.to_numpy(dtype=float)
    matrix = 0.5 * (matrix + matrix.T)
    np.fill_diagonal(matrix, 0.0)
    matrix = np.clip(matrix, 0.0, None)
    return squareform(matrix, checks=False)


def choose_k(dist: pd.DataFrame, z, k_min: int = 3, k_max: int = 8) -> tuple[int, float]:
    n = len(dist)
    k_max = max(k_min, min(k_max, n - 1))
    best_k, best_score = k_min, -1.0
    condensed_ok = n >= k_min + 1
    if not condensed_ok:
        return max(1, n // 2), float("nan")
    for k in range(k_min, k_max + 1):
        labels = fcluster(z, t=k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        try:
            score = float(silhouette_score(dist.to_numpy(), labels, metric="precomputed"))
        except ValueError:
            continue
        if score > best_score:
            best_k, best_score = k, score
    return best_k, best_score


def cluster_from_prices(
    prices: pd.DataFrame,
    *,
    k: int | None = None,
    k_min: int = 3,
    k_max: int = 8,
) -> dict:
    """Average-linkage clustering on Mantegna correlation distance."""
    corr = correlation_matrix(prices)
    dist = correlation_distance(corr)
    z = linkage(_condensed(dist), method="average")
    if k is None:
        k, silhouette = choose_k(dist, z, k_min=k_min, k_max=k_max)
    else:
        labels = fcluster(z, t=k, criterion="maxclust")
        try:
            silhouette = float(silhouette_score(dist.to_numpy(), labels, metric="precomputed"))
        except ValueError:
            silhouette = float("nan")
    labels = fcluster(z, t=k, criterion="maxclust")
    groups: list[dict] = []
    for cluster_id in sorted(set(labels)):
        members = [str(t) for t, lab in zip(dist.index, labels) if lab == cluster_id]
        groups.append({"id": int(cluster_id), "tickers": members, "size": len(members)})
    return {
        "k": int(k),
        "method": "average-linkage",
        "distance": "mantegna",
        "silhouette": None if np.isnan(silhouette) else round(silhouette, 4),
        "groups": groups,
        "labels": {str(t): int(lab) for t, lab in zip(dist.index, labels)},
        "corr": corr,
    }

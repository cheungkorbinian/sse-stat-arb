from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint


@dataclass
class PairCandidate:
    y: str
    x: str
    cluster_id: int
    rho: float
    beta: float
    intercept: float
    coint_pvalue: float
    half_life: float
    spread_mean: float
    spread_std: float

    def to_dict(self) -> dict:
        payload = asdict(self)
        for key, value in payload.items():
            if isinstance(value, float):
                payload[key] = None if np.isnan(value) else round(value, 6)
        return payload


def _ols_hedge(log_y: pd.Series, log_x: pd.Series) -> tuple[float, float, pd.Series]:
    aligned = pd.concat([log_y, log_x], axis=1).dropna()
    aligned.columns = ["y", "x"]
    if len(aligned) < 60:
        raise ValueError("not enough overlapping observations")
    x = sm.add_constant(aligned["x"])
    model = sm.OLS(aligned["y"], x).fit()
    intercept = float(model.params.iloc[0])
    beta = float(model.params.iloc[1])
    spread = aligned["y"] - intercept - beta * aligned["x"]
    return intercept, beta, spread


def half_life(spread: pd.Series) -> float:
    """Ornstein–Uhlenbeck half-life: HL = ln(2) / |λ| from Δs_t = λ s_{t-1} + ε."""
    s = spread.dropna()
    if len(s) < 40:
        return float("inf")
    lag = s.shift(1)
    delta = s.diff()
    frame = pd.concat([delta, lag], axis=1).dropna()
    frame.columns = ["ds", "lag"]
    if frame["lag"].var() == 0:
        return float("inf")
    x = sm.add_constant(frame["lag"])
    lam = float(sm.OLS(frame["ds"], x).fit().params.iloc[1])
    if lam >= 0:
        return float("inf")
    return float(-np.log(2.0) / lam)


def score_pair(prices: pd.DataFrame, y: str, x: str, cluster_id: int) -> PairCandidate | None:
    log_p = np.log(prices[[y, x]].where(prices[[y, x]] > 0)).dropna()
    if len(log_p) < 60:
        return None
    rho = float(log_p[y].diff().corr(log_p[x].diff()))
    try:
        intercept, beta, spread = _ols_hedge(log_p[y], log_p[x])
        pvalue = float(coint(log_p[y], log_p[x], autolag="aic")[1])
    except (ValueError, np.linalg.LinAlgError):
        return None
    hl = half_life(spread)
    return PairCandidate(
        y=y,
        x=x,
        cluster_id=cluster_id,
        rho=rho,
        beta=beta,
        intercept=intercept,
        coint_pvalue=pvalue,
        half_life=hl,
        spread_mean=float(spread.mean()),
        spread_std=float(spread.std(ddof=1) or np.nan),
    )


def select_pairs(
    prices: pd.DataFrame,
    groups: list[dict],
    corr: pd.DataFrame,
    *,
    min_abs_corr: float = 0.5,
    max_pvalue: float = 0.05,
    min_half_life: float = 5.0,
    max_half_life: float = 90.0,
    max_per_cluster: int = 2,
    max_pairs: int = 12,
) -> list[PairCandidate]:
    chosen: list[PairCandidate] = []
    for group in groups:
        members = group["tickers"]
        if len(members) < 2:
            continue
        scored: list[PairCandidate] = []
        for i, y in enumerate(members):
            for x in members[i + 1 :]:
                if y not in corr.index or x not in corr.columns:
                    continue
                rho = corr.loc[y, x]
                if pd.isna(rho) or abs(float(rho)) < min_abs_corr:
                    continue
                candidate = score_pair(prices, y, x, cluster_id=int(group["id"]))
                if candidate is None:
                    continue
                if candidate.coint_pvalue > max_pvalue:
                    continue
                if not (min_half_life <= candidate.half_life <= max_half_life):
                    continue
                if candidate.spread_std is None or candidate.spread_std <= 0:
                    continue
                if not (0.2 <= candidate.beta <= 3.0):
                    continue
                scored.append(candidate)
        scored.sort(key=lambda item: (item.coint_pvalue, -abs(item.rho)))
        chosen.extend(scored[:max_per_cluster])
    chosen.sort(key=lambda item: (item.coint_pvalue, -abs(item.rho)))
    return chosen[:max_pairs]

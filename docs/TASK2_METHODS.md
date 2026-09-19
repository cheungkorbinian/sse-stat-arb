# Task 2 — Methods (A, B, C)

Pairs trading / statistical arbitrage on Shanghai A-shares. Prices are **adjusted close** from the Task 1 MongoDB (`adj_close`), so splits and dividends do not create fake mean-reversion.

The research universe is a liquid SSE subset (banks, insurers, brokers, energy, materials, consumer, industrials) with long Yahoo history. Full-market clustering on ~2,000 names is possible with the same code after `sse-data bootstrap`.

---

## A. Correlation model

Daily log return of stock \(i\):

\[
r_{i,t} = \ln\left(\frac{P_{i,t}}{P_{i,t-1}}\right)
\]

Pearson correlation over a formation window of \(T\) days (252 in the backtest):

\[
\rho_{ij} = \frac{\sum_t (r_{i,t}-\bar r_i)(r_{j,t}-\bar r_j)}
{\sqrt{\sum_t (r_{i,t}-\bar r_i)^2}\sqrt{\sum_t (r_{j,t}-\bar r_j)^2}}
\]

Correlation is **not** a trading signal by itself. Two stocks can be highly correlated and still have a drifting spread. We use \(\rho_{ij}\) as a **filter and clustering feature**, then require cointegration (section C).

Mantegna (1999) metric distance, which is Euclidean on the correlation matrix:

\[
d_{ij} = \sqrt{2(1-\rho_{ij})},\qquad d_{ii}=0
\]

Properties: \(d_{ij}=0\) iff \(\rho_{ij}=1\); \(d_{ij}\) grows as correlation falls. This is the input to clustering.

---

## B. Clustering model

Hierarchical agglomerative clustering, **average linkage**, on \(d_{ij}\).

Merge cost between clusters \(A\) and \(B\):

\[
D(A,B) = \frac{1}{|A||B|}\sum_{i\in A}\sum_{j\in B} d_{ij}
\]

Number of clusters \(k\) is chosen by maximizing the silhouette score on the precomputed distance matrix, \(k \in \{3,\ldots,8\}\).

Rationale: pairs trading is more plausible **inside** an economic group (two banks, two liquor names) than across unrelated sectors. Clustering on return correlation is a data-driven proxy for that grouping when GICS tags are incomplete.

---

## C. Mean-reversion strategy

### Pair selection (inside each cluster)

For every pair \((Y,X)\) in a cluster with \(|\rho_{YX}| \ge 0.5\):

1. **Engle–Granger hedge ratio** on log prices:

\[
\ln P_{Y,t} = \alpha + \beta \ln P_{X,t} + \varepsilon_t
\]

OLS gives \(\hat\alpha,\hat\beta\). The residual is the spread:

\[
s_t = \ln P_{Y,t} - \hat\alpha - \hat\beta \ln P_{X,t}
\]

2. **Cointegration test:** Engle–Granger \(p\)-value on \((\ln P_Y, \ln P_X)\). Keep the pair if \(p < 0.05\).

3. **Half-life** of an Ornstein–Uhlenbeck fit. Estimate \(\lambda\) from

\[
\Delta s_t = \lambda s_{t-1} + u_t
\]

\[
\mathrm{HL} = \frac{\ln 2}{|\lambda|}\quad (\lambda<0)
\]

Keep \(5 \le \mathrm{HL} \le 90\) trading days and hedge ratio \(0.2 \le \hat\beta \le 3\) (a negative β is a long-long bet, not a spread).

Up to 2 pairs per cluster, 12 pairs per window, ranked by cointegration \(p\)-value.

### Signal

Formation-window hedge \(\hat\alpha,\hat\beta\) is **frozen**. During trading, the z-score uses a rolling 60-day mean and standard deviation of \(s_t\) so a slow level shift is not mistaken for a 3.5σ blow-up.

\[
z_t = \frac{s_t - \mu_{t,60}}{\sigma_{t,60}}
\]

| Rule | Condition |
|---|---|
| Short the spread | \(z_t \ge 2\) (Y rich vs X) |
| Long the spread | \(z_t \le -2\) (Y cheap vs X) |
| Exit | \(\lvert z_t\rvert \le 0.5\) |
| Stop | \(\lvert z_t\rvert \ge 4.5\) or 30-day time stop |

Long the spread: long \(Y\), short \(\beta\) units of \(X\). Daily P&amp;L (log-space):

\[
R_t \approx \mathrm{pos}_{t-1}\left(r_{Y,t} - \beta r_{X,t}\right)
\]

**Execution:** signal at close \(t\), fill at close \(t+1\). That removes look-ahead and is consistent with **T+1** on A-shares.

Windows: 252-day formation, 63-day trading, rolled forward. Parameters are never estimated on the days they are traded.

### Costs (China A-share)

Charged on each turnover, as a fraction of one-leg notional:

- Commission \(3\) bps per side
- Slippage \(5\) bps per side
- Stamp duty \(5\) bps on **sells** only

Opening or closing a pair \(\approx 21\) bps of one-leg capital.

**Short-sale caveat:** A-share securities lending (融资融券) is limited and expensive. The backtest assumes a short leg is available at the slippage above. That is the standard academic assumption; live trading would need a borrow filter or a long-only spread.

---

## D. Backtest (summary)

See `docs/SSE_StatArb_Slides.pptx` for the submission deck, and `data/research/task2_results.json` for numbers.

Metrics: total return, CAGR, annualized Sharpe (252), max drawdown, number of round-trips, average holding days, stop-exit count.

Equal weight across active pairs in a window. Idle days count as zero return.

"""
Multi-Criteria Capacitated Supplier Selection Problem (MC-CSSP)
Inspired by OR-Library benchmark instances and UCI supplier datasets.

Decision: Select K suppliers from N candidates to fulfil aggregated demand
under four conflicting criteria (cost, quality, lead-time, reliability)
plus realistic non-linear effects:

  - Pairwise SYNERGY matrix S (positive/negative interactions between
    suppliers — represents geographic / technological compatibility)
  - RISK penalty (variance of reliability across selected suppliers)
  - DIVERSIFICATION bonus (sector / region coverage)
  - NON-LINEAR capacity term  (saturating reward for buffer over demand)
  - WORST-CASE lead time term (max instead of mean — bottleneck effect)

These non-linear couplings break the trivial top-K-by-weighted-score
optimum, making the problem NP-hard in practice and meaningful for
metaheuristic comparison.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field


@dataclass
class MCSSPInstance:
    name: str
    N: int
    K: int
    cost: np.ndarray
    quality: np.ndarray
    lead_time: np.ndarray
    reliability: np.ndarray
    capacity: np.ndarray
    sector: np.ndarray            # categorical sector id, length N
    synergy: np.ndarray           # NxN pairwise synergy matrix (zero diagonal)
    demand: float
    weights: np.ndarray
    n_sectors: int = 5

    def criteria_matrix(self) -> np.ndarray:
        return np.column_stack([self.cost, self.quality, self.lead_time, self.reliability])

    def benefit_mask(self) -> np.ndarray:
        return np.array([False, True, False, True])


def generate_instance(name: str, N: int = 20, K: int = 8, seed: int = 42,
                      n_sectors: int = 5) -> MCSSPInstance:
    rng = np.random.default_rng(seed)
    cost = rng.uniform(40.0, 120.0, size=N)
    quality = rng.uniform(55.0, 98.0, size=N)
    lead_time = rng.uniform(3.0, 25.0, size=N)
    reliability = rng.uniform(0.60, 0.99, size=N)
    capacity = rng.uniform(80.0, 220.0, size=N)
    sector = rng.integers(0, n_sectors, size=N)

    # Pairwise synergy: structured (same-sector tend to have positive synergy
    # but with strong noise so it is non-trivial); rescaled to small magnitude.
    base = rng.standard_normal((N, N)) * 0.04
    base = (base + base.T) / 2.0
    same_sector = (sector[:, None] == sector[None, :]).astype(float)
    synergy = base + 0.05 * (same_sector - 0.5)
    np.fill_diagonal(synergy, 0.0)

    demand = 0.55 * capacity.sum() * (K / N)
    weights = np.array([0.30, 0.30, 0.20, 0.20])
    return MCSSPInstance(name, N, K, cost, quality, lead_time, reliability,
                         capacity, sector, synergy, demand, weights, n_sectors)


def evaluate_selection(inst: MCSSPInstance, selection: np.ndarray) -> dict:
    sel = selection.astype(bool)
    if sel.sum() != inst.K:
        return dict(feasible=False, utility=-1e9, cost=np.inf, quality=0.0,
                    lead_time=np.inf, reliability=0.0, capacity_slack=-np.inf,
                    synergy_term=0.0, risk_term=0.0, diversity_term=0.0)

    total_capacity = inst.capacity[sel].sum()
    capacity_slack = total_capacity - inst.demand
    feasible = capacity_slack >= 0.0

    cmat = inst.criteria_matrix()
    benefit = inst.benefit_mask()
    norm = np.zeros_like(cmat)
    for j in range(4):
        col = cmat[:, j]
        rng_j = col.max() - col.min() + 1e-12
        norm[:, j] = (col - col.min()) / rng_j if benefit[j] else (col.max() - col) / rng_j

    # Linear core (mean of normalized criteria; lead_time uses MAX => bottleneck)
    sel_norm = norm[sel].copy()
    sel_norm[:, 2] = (norm[sel, 2].min())            # bottleneck transform: replace lead_time
    avg = sel_norm.mean(axis=0)
    linear = float(inst.weights @ avg)

    # Pairwise synergy
    S = inst.synergy[np.ix_(sel, sel)]
    synergy_term = float(S.sum() / (inst.K * (inst.K - 1) + 1e-12))

    # Risk penalty (variance of reliability — lower is better)
    risk_term = float(-0.6 * np.var(inst.reliability[sel]))

    # Sector diversification bonus
    secs = inst.sector[sel]
    coverage = len(np.unique(secs)) / inst.n_sectors
    diversity_term = 0.10 * coverage

    # Non-linear capacity buffer reward (saturating)
    buffer_ratio = max(0.0, capacity_slack) / (inst.demand + 1e-12)
    capacity_term = 0.05 * (1.0 - np.exp(-3.0 * buffer_ratio))

    utility = linear + synergy_term + risk_term + diversity_term + capacity_term
    if not feasible:
        utility -= 0.5

    return dict(
        feasible=feasible,
        utility=utility,
        cost=float(inst.cost[sel].mean()),
        quality=float(inst.quality[sel].mean()),
        lead_time=float(inst.lead_time[sel].max()),     # report bottleneck
        reliability=float(inst.reliability[sel].mean()),
        capacity_slack=float(capacity_slack),
        synergy_term=synergy_term,
        risk_term=risk_term,
        diversity_term=diversity_term,
    )

"""
Real-world-style supplier instance based on published characteristics
of automotive and electronics supplier panels (Sevkli et al., 2008;
Yousefi Babadi et al., 2025; Asadi et al., 2025).

Suppliers are drawn from 5 sectors with realistic correlation structure:
  - Cost negatively correlates with quality (premium suppliers)
  - Reliability positively correlates with lead time (slower but stable)
  - Capacity scaled by sector
"""

from __future__ import annotations
import numpy as np
from benchmarks.problem import MCSSPInstance


def generate_realworld_instance(name: str = "MC-CSSP-RW",
                                N: int = 30, K: int = 12, seed: int = 7) -> MCSSPInstance:
    rng = np.random.default_rng(seed)
    n_sectors = 5
    sector = rng.integers(0, n_sectors, size=N)

    # Latent quality factor in [0,1] driving correlations
    latent_q = rng.beta(2.5, 2.5, size=N)

    # Cost: higher quality = higher cost, with noise
    cost = 50 + 70 * latent_q + 12 * rng.standard_normal(N)
    cost = np.clip(cost, 35.0, 140.0)

    # Quality: directly tied to latent factor
    quality = 55 + 42 * latent_q + 4 * rng.standard_normal(N)
    quality = np.clip(quality, 50.0, 99.0)

    # Lead time: high reliability suppliers are slower (premium)
    lead_time = 4 + 18 * (0.5 + 0.5 * latent_q) + 3 * rng.standard_normal(N)
    lead_time = np.clip(lead_time, 2.0, 30.0)

    # Reliability: correlated with quality but separately noised
    reliability = 0.65 + 0.30 * latent_q + 0.05 * rng.standard_normal(N)
    reliability = np.clip(reliability, 0.55, 0.99)

    # Capacity by sector tier
    sector_tier = np.array([180, 140, 110, 95, 80])
    capacity = sector_tier[sector] + 25 * rng.standard_normal(N)
    capacity = np.clip(capacity, 60.0, 240.0)

    # Synergy: same-sector + supplier-quality similarity
    base = rng.standard_normal((N, N)) * 0.04
    base = (base + base.T) / 2.0
    same_sector = (sector[:, None] == sector[None, :]).astype(float)
    qsim = 1.0 - np.abs(latent_q[:, None] - latent_q[None, :])
    synergy = base + 0.04 * (same_sector - 0.5) + 0.03 * (qsim - 0.5)
    np.fill_diagonal(synergy, 0.0)

    demand = 0.50 * capacity.sum() * (K / N)
    weights = np.array([0.30, 0.30, 0.20, 0.20])

    return MCSSPInstance(name, N, K, cost, quality, lead_time, reliability,
                         capacity, sector, synergy, demand, weights, n_sectors)

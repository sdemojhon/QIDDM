"""
Quantum-Inspired Dynamic Decision-Making (QIDDM)
================================================

Proposed framework for the Multi-Criteria Capacitated Supplier Selection
Problem (MC-CSSP).

ARCHITECTURE
------------
1. Q-bit population
       Each chromosome is a vector of N q-bits (alpha_i, beta_i),
       |alpha_i|^2 + |beta_i|^2 = 1.  P(bit_i = 1) = |beta_i|^2.

2. Multi-criteria warm start
       Initial amplitudes are biased by criteria-weighted scores so the
       superposition is centred on a high-quality region while still
       covering the search space.

3. Han-Kim rotation gate with dynamic angle
       theta_t = theta_max * exp(-decay * t / T) + jitter when stagnating.
       Direction selected from the standard quantum-evolutionary lookup
       table that drives |beta| -> 1 when gbest selects the position and
       |alpha| -> 1 when it deselects.

4. Multi-criteria interference modulation
       Per-position interference vector boosts rotations on positions
       that improve the criteria currently weakest in gbest, providing
       built-in multi-criteria balance.

5. Q-NOT mutation (quantum diversification)
       With small probability swap (alpha, beta) on selected bits — a
       quantum analogue of bit-flip mutation that preserves probability
       mass.

6. Decision-aware local search
       Every L iterations the algorithm performs criteria-guided
       1-swap and 2-swap moves around gbest using the interference
       vector to focus on promising swaps.
"""

from __future__ import annotations
import time
import numpy as np
from benchmarks.problem import MCSSPInstance, evaluate_selection


# --------------------------------------------------------------------------- #
def _measure(beta_sq: np.ndarray, K: int, rng: np.random.Generator,
             stochastic: bool = True) -> np.ndarray:
    """Collapse one chromosome to a length-K binary selection."""
    sel = np.zeros_like(beta_sq, dtype=int)
    if stochastic:
        # tilt scores with probability + small noise then take top-K
        score = beta_sq + 0.05 * rng.standard_normal(beta_sq.shape)
    else:
        score = beta_sq
    idx = np.argsort(-score)[:K]
    sel[idx] = 1
    return sel


def _criteria_norm(inst: MCSSPInstance) -> np.ndarray:
    cmat = inst.criteria_matrix()
    benefit = inst.benefit_mask()
    norm = np.zeros_like(cmat)
    for j in range(4):
        col = cmat[:, j]
        rng_j = col.max() - col.min() + 1e-12
        norm[:, j] = (col - col.min()) / rng_j if benefit[j] else (col.max() - col) / rng_j
    return norm


def _interference(inst: MCSSPInstance, gbest: np.ndarray,
                  norm: np.ndarray) -> np.ndarray:
    g_avg = norm[gbest.astype(bool)].mean(axis=0)
    weak = (1.0 - g_avg)
    weak = weak / (weak.sum() + 1e-12)
    interference = norm @ weak
    lo, hi = interference.min(), interference.max()
    return 2.0 * (interference - lo) / (hi - lo + 1e-12) - 1.0


def _hankim_direction(xj: int, bj: int, fx: float, fb: float,
                      alpha: float, beta: float) -> int:
    """Han-Kim look-up: returns +1, -1 or 0 — sign of theta to apply."""
    ab = alpha * beta
    if xj == 0 and bj == 1:
        if ab > 0:
            return +1
        if ab < 0:
            return -1
        return +1 if alpha == 0 else 0
    if xj == 1 and bj == 0:
        if fx >= fb:
            if ab > 0:
                return -1
            if ab < 0:
                return +1
            return -1 if beta == 0 else 0
        else:
            if ab > 0:
                return +1
            if ab < 0:
                return -1
            return 0
    if xj == 1 and bj == 1:
        if ab > 0:
            return +1
        if ab < 0:
            return -1
        return +1 if alpha == 0 else 0
    if xj == 0 and bj == 0:
        if ab > 0:
            return -1
        if ab < 0:
            return +1
        return -1 if beta == 0 else 0
    return 0


def _local_search(inst: MCSSPInstance, sel: np.ndarray, fitness: float,
                  interference: np.ndarray, max_swaps: int = 6) -> tuple:
    """1-swap criteria-guided local search around current selection."""
    sel = sel.copy()
    improved = True
    inside = np.where(sel == 1)[0]
    outside = np.where(sel == 0)[0]
    # Promising drop = lowest interference among inside
    # Promising add  = highest interference among outside
    drops = inside[np.argsort(interference[inside])[:max_swaps]]
    adds = outside[np.argsort(-interference[outside])[:max_swaps]]
    while improved:
        improved = False
        for d in drops:
            for a in adds:
                if sel[d] == 1 and sel[a] == 0:
                    trial = sel.copy()
                    trial[d] = 0
                    trial[a] = 1
                    f_new = evaluate_selection(inst, trial)["utility"]
                    if f_new > fitness + 1e-9:
                        sel = trial
                        fitness = f_new
                        improved = True
                        break
            if improved:
                break
    return sel, fitness


# --------------------------------------------------------------------------- #
def run_qiddm(inst: MCSSPInstance,
              pop_size: int = 40,
              generations: int = 100,
              theta_max: float = 0.10 * np.pi,
              theta_min: float = 0.01 * np.pi,
              decay: float = 3.0,
              eta_interference: float = 0.30,
              q_not_prob: float = 0.02,
              local_every: int = 8,
              warm_start: bool = True,
              seed: int = 0) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    N, K = inst.N, inst.K
    T = generations
    norm = _criteria_norm(inst)

    # ---- multi-criteria warm-start amplitudes ----
    if warm_start:
        base_score = norm @ inst.weights
        p_init = 0.5 + 0.25 * (2.0 * (base_score - base_score.min())
                               / (base_score.max() - base_score.min() + 1e-12) - 1.0)
        p_init = np.clip(p_init, 0.15, 0.85)
    else:
        p_init = np.full(N, 0.5)
    beta = np.sqrt(p_init)
    alpha = np.sqrt(1.0 - p_init)
    alpha = np.tile(alpha, (pop_size, 1))
    beta = np.tile(beta, (pop_size, 1))

    # tiny perturbation per chromosome for population diversity
    perturb = 0.05 * rng.standard_normal((pop_size, N))
    beta = np.clip(beta + perturb, 0.05, 0.99)
    alpha = np.sqrt(np.clip(1.0 - beta ** 2, 1e-6, 1.0))

    # ---- initial measurement ----
    pop_sel = np.array([_measure(beta[i] ** 2, K, rng) for i in range(pop_size)])
    fitness = np.array([evaluate_selection(inst, s)["utility"] for s in pop_sel])
    g_idx = int(np.argmax(fitness))
    gbest = pop_sel[g_idx].copy()
    gbest_fit = float(fitness[g_idx])
    best_hist = [gbest_fit]

    stag_counter = 0
    prev_best = gbest_fit

    for t in range(T):
        # adaptive angle
        improved_recently = (gbest_fit > prev_best + 1e-9)
        stag_counter = 0 if improved_recently else stag_counter + 1
        prev_best = gbest_fit
        jitter = 0.5 * theta_max if stag_counter > 5 else 0.0
        theta_t = theta_max * np.exp(-decay * t / T) + theta_min + jitter

        # interference
        I = _interference(inst, gbest, norm)

        # ---- vectorized rotation (Han-Kim direction matrix) ----
        # Build P x N direction matrix using vectorized rules.
        x_mat = pop_sel
        g_row = gbest[None, :]
        f_better = (fitness < gbest_fit)[:, None]   # P x 1
        ab = alpha * beta
        ab_pos = ab > 0
        ab_neg = ab < 0

        # Cases as in Han-Kim look-up
        c01 = (x_mat == 0) & (g_row == 1)                   # want bit=1
        c10_better = (x_mat == 1) & (g_row == 0) & f_better  # want bit=1
        c10_worse = (x_mat == 1) & (g_row == 0) & ~f_better  # want bit=0
        c11 = (x_mat == 1) & (g_row == 1)                   # want bit=1
        c00 = (x_mat == 0) & (g_row == 0)                   # want bit=0

        want_one = c01 | c10_better | c11
        want_zero = c10_worse | c00
        d_mat = np.zeros_like(alpha)
        d_mat[want_one & ab_pos] = +1
        d_mat[want_one & ab_neg] = -1
        d_mat[want_zero & ab_pos] = -1
        d_mat[want_zero & ab_neg] = +1
        # Edge cases (alpha==0 or beta==0) are rare with renormalization;
        # keep direction 0 there.

        phase = d_mat * theta_t * (1.0 + eta_interference * I[None, :])
        cos_p = np.cos(phase)
        sin_p = np.sin(phase)
        new_alpha = cos_p * alpha - sin_p * beta
        new_beta = sin_p * alpha + cos_p * beta
        alpha[:] = new_alpha
        beta[:] = new_beta

        # Q-NOT mutation
        flip = rng.random((pop_size, N)) < q_not_prob
        alpha[flip], beta[flip] = beta[flip], alpha[flip]

        # renormalize
        nrm = np.sqrt(alpha ** 2 + beta ** 2) + 1e-12
        alpha /= nrm
        beta /= nrm

        # measurement
        pop_sel = np.array([_measure(beta[i] ** 2, K, rng) for i in range(pop_size)])
        fitness = np.array([evaluate_selection(inst, s)["utility"] for s in pop_sel])
        g_idx = int(np.argmax(fitness))
        if fitness[g_idx] > gbest_fit:
            gbest = pop_sel[g_idx].copy()
            gbest_fit = float(fitness[g_idx])

        # ---- decision-aware local search every L generations ----
        if (t + 1) % local_every == 0:
            gbest, gbest_fit = _local_search(inst, gbest, gbest_fit, I)

        best_hist.append(gbest_fit)

    res = evaluate_selection(inst, gbest)
    return dict(method="QIDDM", selection=gbest, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=best_hist,
                detail=res)

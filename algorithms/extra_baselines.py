"""
Extra baselines for QIDDM paper:
    QEA   — Classical Han-Kim Quantum-Inspired Evolutionary Algorithm
            (static rotation, scalar fitness — canonical 2002 design)
    EXACT — Exhaustive enumeration over C(N,K) (small instances only)
"""

from __future__ import annotations
import time
import numpy as np
from itertools import combinations
from benchmarks.problem import MCSSPInstance, evaluate_selection


# --------------------------------------------------------------------------- #
# Classical Han-Kim QEA (2002) — static theta, no interference, no local search
# --------------------------------------------------------------------------- #
def _hk_dir(xj, bj, fx, fb, alpha, beta):
    ab = alpha * beta
    if xj == 0 and bj == 1:
        return +1 if ab > 0 else (-1 if ab < 0 else (+1 if alpha == 0 else 0))
    if xj == 1 and bj == 0:
        if fx >= fb:
            return -1 if ab > 0 else (+1 if ab < 0 else (-1 if beta == 0 else 0))
        return +1 if ab > 0 else (-1 if ab < 0 else 0)
    if xj == 1 and bj == 1:
        return +1 if ab > 0 else (-1 if ab < 0 else (+1 if alpha == 0 else 0))
    if xj == 0 and bj == 0:
        return -1 if ab > 0 else (+1 if ab < 0 else (-1 if beta == 0 else 0))
    return 0


def _measure_topk(beta_sq, K, rng):
    sel = np.zeros_like(beta_sq, dtype=int)
    score = beta_sq + 0.05 * rng.standard_normal(beta_sq.shape)
    idx = np.argsort(-score)[:K]
    sel[idx] = 1
    return sel


def run_qea(inst: MCSSPInstance, pop_size: int = 40, generations: int = 100,
            theta: float = 0.05 * np.pi, seed: int = 0) -> dict:
    """Canonical Han-Kim QEA (2002) — static rotation, scalar fitness only."""
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    N, K = inst.N, inst.K

    alpha = np.full((pop_size, N), 1.0 / np.sqrt(2.0))
    beta = np.full((pop_size, N), 1.0 / np.sqrt(2.0))

    pop_sel = np.array([_measure_topk(beta[i] ** 2, K, rng) for i in range(pop_size)])
    fit = np.array([evaluate_selection(inst, s)["utility"] for s in pop_sel])
    g = pop_sel[int(np.argmax(fit))].copy()
    gf = float(fit.max())
    hist = [gf]

    for _ in range(generations):
        # Vectorized Han-Kim rotation
        x_mat = pop_sel
        g_row = g[None, :]
        f_better = (fit < gf)[:, None]
        ab = alpha * beta
        ab_pos = ab > 0
        ab_neg = ab < 0
        c01 = (x_mat == 0) & (g_row == 1)
        c10_b = (x_mat == 1) & (g_row == 0) & f_better
        c10_w = (x_mat == 1) & (g_row == 0) & ~f_better
        c11 = (x_mat == 1) & (g_row == 1)
        c00 = (x_mat == 0) & (g_row == 0)
        want_one = c01 | c10_b | c11
        want_zero = c10_w | c00
        d_mat = np.zeros_like(alpha)
        d_mat[want_one & ab_pos] = +1
        d_mat[want_one & ab_neg] = -1
        d_mat[want_zero & ab_pos] = -1
        d_mat[want_zero & ab_neg] = +1
        phase = d_mat * theta
        cp = np.cos(phase); sp = np.sin(phase)
        new_a = cp * alpha - sp * beta
        new_b = sp * alpha + cp * beta
        alpha[:] = new_a; beta[:] = new_b
        nrm = np.sqrt(alpha ** 2 + beta ** 2) + 1e-12
        alpha /= nrm
        beta /= nrm
        pop_sel = np.array([_measure_topk(beta[i] ** 2, K, rng) for i in range(pop_size)])
        fit = np.array([evaluate_selection(inst, s)["utility"] for s in pop_sel])
        if fit.max() > gf:
            g = pop_sel[int(np.argmax(fit))].copy()
            gf = float(fit.max())
        hist.append(gf)

    res = evaluate_selection(inst, g)
    return dict(method="QEA", selection=g, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=hist, detail=res)


# --------------------------------------------------------------------------- #
# Exact enumeration (gold-standard upper bound for small instances)
# --------------------------------------------------------------------------- #
def run_exact(inst: MCSSPInstance, time_limit_s: float = 60.0) -> dict:
    """Brute force C(N,K) — feasible for small N (e.g. N=20, K=8 ≈ 125k combos)."""
    t0 = time.perf_counter()
    N, K = inst.N, inst.K
    best_sel = None
    best_u = -np.inf
    try:
        from math import comb
        n_combos = comb(N, K)
        if n_combos > 5_000_000:
            return dict(method="EXACT", selection=None, utility=np.nan,
                        cpu_time=0.0, convergence=[], detail=dict(skipped=True),
                        n_combos=n_combos)
    except Exception:
        pass

    template = np.zeros(N, dtype=int)
    for combo in combinations(range(N), K):
        if time.perf_counter() - t0 > time_limit_s:
            break
        sel = template.copy()
        sel[list(combo)] = 1
        u = evaluate_selection(inst, sel)["utility"]
        if u > best_u:
            best_u = u
            best_sel = sel
    res = evaluate_selection(inst, best_sel) if best_sel is not None else {}
    return dict(method="EXACT", selection=best_sel, utility=float(best_u),
                cpu_time=time.perf_counter() - t0,
                convergence=[float(best_u)], detail=res)

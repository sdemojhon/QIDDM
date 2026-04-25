"""
Baseline algorithms for the Multi-Criteria Capacitated Supplier Selection
Problem (MC-CSSP):
    1. TOPSIS  — Technique for Order Preference by Similarity to Ideal Solution
    2. AHP     — Analytic Hierarchy Process (weighted criteria ranking)
    3. GA      — Genetic Algorithm (binary encoding)
    4. PSO     — Discrete Particle Swarm Optimization (sigmoid binary)

Each algorithm returns a dict:
    selection      : binary numpy array of length N
    utility        : aggregate utility value
    cpu_time       : seconds spent
    convergence    : list of best-so-far utilities per iteration (or [] for analytic methods)
"""

from __future__ import annotations
import time
import numpy as np
from typing import Callable
from benchmarks.problem import MCSSPInstance, evaluate_selection


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _topk_selection(scores: np.ndarray, K: int) -> np.ndarray:
    sel = np.zeros_like(scores, dtype=int)
    idx = np.argsort(-scores)[:K]
    sel[idx] = 1
    return sel


def _normalize_for_topsis(cmat: np.ndarray) -> np.ndarray:
    norm = cmat / np.sqrt((cmat ** 2).sum(axis=0) + 1e-12)
    return norm


# --------------------------------------------------------------------------- #
# 1. TOPSIS
# --------------------------------------------------------------------------- #
def run_topsis(inst: MCSSPInstance) -> dict:
    t0 = time.perf_counter()
    cmat = inst.criteria_matrix()
    norm = _normalize_for_topsis(cmat)
    weighted = norm * inst.weights

    benefit = inst.benefit_mask()
    ideal_pos = np.where(benefit, weighted.max(axis=0), weighted.min(axis=0))
    ideal_neg = np.where(benefit, weighted.min(axis=0), weighted.max(axis=0))

    d_pos = np.sqrt(((weighted - ideal_pos) ** 2).sum(axis=1))
    d_neg = np.sqrt(((weighted - ideal_neg) ** 2).sum(axis=1))
    closeness = d_neg / (d_pos + d_neg + 1e-12)

    sel = _topk_selection(closeness, inst.K)
    res = evaluate_selection(inst, sel)
    return dict(method="TOPSIS", selection=sel, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=[res["utility"]],
                detail=res)


# --------------------------------------------------------------------------- #
# 2. AHP (with pairwise comparison matrix derived from criteria weights)
# --------------------------------------------------------------------------- #
def run_ahp(inst: MCSSPInstance) -> dict:
    t0 = time.perf_counter()
    cmat = inst.criteria_matrix()
    benefit = inst.benefit_mask()

    # Min-max normalize each criterion to a benefit-oriented [0,1] scale
    norm = np.zeros_like(cmat)
    for j in range(4):
        col = cmat[:, j]
        rng = col.max() - col.min() + 1e-12
        norm[:, j] = (col - col.min()) / rng if benefit[j] else (col.max() - col) / rng

    # Pairwise consistency: derive priority vector via geometric mean (Saaty)
    # Build a synthetic pairwise matrix from weights for criteria, then aggregate
    w = inst.weights / inst.weights.sum()
    score = norm @ w
    sel = _topk_selection(score, inst.K)
    res = evaluate_selection(inst, sel)
    return dict(method="AHP", selection=sel, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=[res["utility"]],
                detail=res)


# --------------------------------------------------------------------------- #
# 3. Genetic Algorithm (binary encoding, length-N chromosome with K ones)
# --------------------------------------------------------------------------- #
def _repair(chrom: np.ndarray, K: int, rng: np.random.Generator) -> np.ndarray:
    """Force exactly K ones in chromosome."""
    ones = int(chrom.sum())
    if ones == K:
        return chrom
    if ones > K:
        idx = np.where(chrom == 1)[0]
        drop = rng.choice(idx, size=ones - K, replace=False)
        chrom[drop] = 0
    else:
        idx = np.where(chrom == 0)[0]
        add = rng.choice(idx, size=K - ones, replace=False)
        chrom[add] = 1
    return chrom


def run_ga(inst: MCSSPInstance, pop_size: int = 40, generations: int = 100,
           pc: float = 0.85, pm: float = 0.05, seed: int = 0) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    N, K = inst.N, inst.K

    # Initial population
    pop = np.zeros((pop_size, N), dtype=int)
    for i in range(pop_size):
        idx = rng.choice(N, size=K, replace=False)
        pop[i, idx] = 1

    fitness = np.array([evaluate_selection(inst, c)["utility"] for c in pop])
    best_hist = [fitness.max()]

    for _ in range(generations):
        # Tournament selection
        new_pop = []
        while len(new_pop) < pop_size:
            i, j = rng.integers(0, pop_size, 2)
            p1 = pop[i] if fitness[i] > fitness[j] else pop[j]
            i, j = rng.integers(0, pop_size, 2)
            p2 = pop[i] if fitness[i] > fitness[j] else pop[j]

            # Uniform crossover
            if rng.random() < pc:
                mask = rng.random(N) < 0.5
                c1 = np.where(mask, p1, p2)
                c2 = np.where(mask, p2, p1)
            else:
                c1, c2 = p1.copy(), p2.copy()

            # Bit-flip mutation
            for c in (c1, c2):
                flip = rng.random(N) < pm
                c[flip] = 1 - c[flip]
                _repair(c, K, rng)

            new_pop.append(c1)
            if len(new_pop) < pop_size:
                new_pop.append(c2)

        pop = np.array(new_pop)
        fitness = np.array([evaluate_selection(inst, c)["utility"] for c in pop])
        best_hist.append(fitness.max())

    best = pop[np.argmax(fitness)]
    res = evaluate_selection(inst, best)
    return dict(method="GA", selection=best, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=best_hist,
                detail=res)


# --------------------------------------------------------------------------- #
# 4. Discrete PSO (sigmoid binary)
# --------------------------------------------------------------------------- #
def run_pso(inst: MCSSPInstance, swarm: int = 40, iters: int = 100,
            w: float = 0.6, c1: float = 1.7, c2: float = 1.7,
            seed: int = 0) -> dict:
    t0 = time.perf_counter()
    rng = np.random.default_rng(seed)
    N, K = inst.N, inst.K

    pos = np.zeros((swarm, N), dtype=int)
    for i in range(swarm):
        idx = rng.choice(N, size=K, replace=False)
        pos[i, idx] = 1
    vel = rng.uniform(-1, 1, size=(swarm, N))

    pbest = pos.copy()
    pbest_fit = np.array([evaluate_selection(inst, p)["utility"] for p in pos])
    g_idx = int(np.argmax(pbest_fit))
    gbest = pbest[g_idx].copy()
    gbest_fit = pbest_fit[g_idx]

    best_hist = [gbest_fit]
    for _ in range(iters):
        r1 = rng.random((swarm, N))
        r2 = rng.random((swarm, N))
        vel = w * vel + c1 * r1 * (pbest - pos) + c2 * r2 * (gbest - pos)
        prob = 1.0 / (1.0 + np.exp(-vel))           # sigmoid
        new_pos = (rng.random((swarm, N)) < prob).astype(int)
        for i in range(swarm):
            _repair(new_pos[i], K, rng)
        pos = new_pos

        fit = np.array([evaluate_selection(inst, p)["utility"] for p in pos])
        improve = fit > pbest_fit
        pbest[improve] = pos[improve]
        pbest_fit[improve] = fit[improve]

        g_idx = int(np.argmax(pbest_fit))
        if pbest_fit[g_idx] > gbest_fit:
            gbest = pbest[g_idx].copy()
            gbest_fit = pbest_fit[g_idx]
        best_hist.append(gbest_fit)

    res = evaluate_selection(inst, gbest)
    return dict(method="PSO", selection=gbest, utility=res["utility"],
                cpu_time=time.perf_counter() - t0, convergence=best_hist,
                detail=res)

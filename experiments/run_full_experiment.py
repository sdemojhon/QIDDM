"""
Comprehensive experimental suite for the QIDDM paper:

  1. Main comparison    : 5 instances × 7 methods × 20 runs
                          (TOPSIS, AHP, GA, PSO, QEA, QIDDM, EXACT-when-feasible)
  2. Ablation study     : QIDDM full vs noDyn / noInt / noLS / noWarm
  3. Scaling study      : utility & runtime vs N (extra-large N = 200)
  4. Sensitivity study  : eta, theta_max, decay sweeps on MC-CSSP-M
  5. Statistical tests  : Mann-Whitney U + Friedman + effect sizes
"""

from __future__ import annotations
import os, sys, json
import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from benchmarks.problem import generate_instance
from benchmarks.realworld import generate_realworld_instance
from algorithms.baselines import run_topsis, run_ahp, run_ga, run_pso
from algorithms.extra_baselines import run_qea, run_exact
from algorithms.qiddm import run_qiddm
from algorithms.qiddm_ablation import (run_qiddm_no_dynamic,
                                       run_qiddm_no_interference,
                                       run_qiddm_no_local_search,
                                       run_qiddm_no_warmstart)


# ------------------------------------------------------------------ #
INSTANCES = [
    ("MC-CSSP-S",   generate_instance,            dict(N=20,  K=8,  seed=42)),
    ("MC-CSSP-M",   generate_instance,            dict(N=40,  K=15, seed=123)),
    ("MC-CSSP-L",   generate_instance,            dict(N=80,  K=30, seed=2026)),
    ("MC-CSSP-XL",  generate_instance,            dict(N=200, K=70, seed=314)),
    ("MC-CSSP-RW",  generate_realworld_instance,  dict(N=30,  K=12, seed=7)),
]

RUNS = 20
GENS = 120
POP = 40
RES_DIR = os.path.join(ROOT, "results")
os.makedirs(RES_DIR, exist_ok=True)


def iter_to_best(history):
    if not history:
        return 0
    best = max(history)
    for i, v in enumerate(history):
        if abs(v - best) < 1e-9:
            return i
    return len(history) - 1


# ------------------------------------------------------------------ #
def main_comparison():
    rows, conv = [], {}
    for name, gen, kw in INSTANCES:
        inst = gen(name=name, **kw) if "name" in gen.__code__.co_varnames else gen(name, **kw)
        print(f"\n=== {name} (N={inst.N}, K={inst.K}) ===")

        # Deterministic
        for fn, label in [(run_topsis, "TOPSIS"), (run_ahp, "AHP")]:
            r = fn(inst)
            rows.append(_row(name, label, 0, r))
            conv[(name, label, 0)] = np.array(r["convergence"])
            print(f"  {label:8s} util={r['utility']:.4f}")

        # Stochastic
        for fn, label in [(run_ga, "GA"), (run_pso, "PSO"),
                          (run_qea, "QEA"), (run_qiddm, "QIDDM")]:
            print(f"  {label:8s}", end=" ", flush=True)
            for s in range(RUNS):
                kwargs = dict(seed=s)
                if label == "GA":
                    r = fn(inst, pop_size=POP, generations=GENS, **kwargs)
                elif label == "PSO":
                    r = fn(inst, swarm=POP, iters=GENS, **kwargs)
                elif label == "QEA":
                    r = fn(inst, pop_size=POP, generations=GENS, **kwargs)
                else:
                    r = fn(inst, pop_size=POP, generations=GENS, **kwargs)
                rows.append(_row(name, label, s, r))
                conv[(name, label, s)] = np.array(r["convergence"])
                print(".", end="", flush=True)
            print()

        # Exact only for small instance
        if inst.N <= 20:
            print("  EXACT", end=" ", flush=True)
            r = run_exact(inst, time_limit_s=120)
            if r["selection"] is not None:
                rows.append(_row(name, "EXACT", 0, r))
                conv[(name, "EXACT", 0)] = np.array(r["convergence"])
                print(f"util={r['utility']:.4f} (t={r['cpu_time']:.1f}s)")

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES_DIR, "main_per_run.csv"), index=False)
    np.savez_compressed(os.path.join(RES_DIR, "main_convergence.npz"),
                        **{f"{k[0]}__{k[1]}__{k[2]}": v for k, v in conv.items()})

    agg = df.groupby(["instance", "method"]).agg(
        util_mean=("utility", "mean"), util_std=("utility", "std"),
        util_best=("utility", "max"), cpu_mean=("cpu_time", "mean"),
        iter_mean=("iterations_to_best", "mean"),
    ).round(4).reset_index()
    agg.to_csv(os.path.join(RES_DIR, "main_summary.csv"), index=False)
    print("\n", agg.to_string(index=False))
    return df, agg


def _row(name, label, run, r):
    d = r.get("detail", {})
    return dict(instance=name, method=label, run=run,
                utility=r["utility"], cpu_time=r["cpu_time"],
                iterations_to_best=iter_to_best(r.get("convergence", [])),
                cost=d.get("cost", np.nan),
                quality=d.get("quality", np.nan),
                lead_time=d.get("lead_time", np.nan),
                reliability=d.get("reliability", np.nan),
                capacity_slack=d.get("capacity_slack", np.nan))


# ------------------------------------------------------------------ #
def ablation_study():
    print("\n\n=== ABLATION ===")
    rows = []
    inst_specs = [("MC-CSSP-M",  generate_instance, dict(N=40, K=15, seed=123)),
                  ("MC-CSSP-L",  generate_instance, dict(N=80, K=30, seed=2026))]
    methods = [
        ("QIDDM-full",  run_qiddm),
        ("QIDDM-noDyn", run_qiddm_no_dynamic),
        ("QIDDM-noInt", run_qiddm_no_interference),
        ("QIDDM-noLS",  run_qiddm_no_local_search),
        ("QIDDM-noWarm", run_qiddm_no_warmstart),
    ]
    for name, gen, kw in inst_specs:
        inst = gen(name, **kw)
        print(f"\n {name}")
        for label, fn in methods:
            print(f"  {label:14s}", end=" ", flush=True)
            for s in range(RUNS):
                r = fn(inst, pop_size=POP, generations=GENS, seed=s)
                rows.append(dict(instance=name, method=label, run=s,
                                 utility=r["utility"],
                                 cpu_time=r["cpu_time"]))
                print(".", end="", flush=True)
            print()
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES_DIR, "ablation_per_run.csv"), index=False)
    agg = df.groupby(["instance", "method"]).agg(
        util_mean=("utility", "mean"), util_std=("utility", "std"),
        util_best=("utility", "max")).round(4).reset_index()
    agg.to_csv(os.path.join(RES_DIR, "ablation_summary.csv"), index=False)
    print(agg.to_string(index=False))
    return df, agg


# ------------------------------------------------------------------ #
def sensitivity_study():
    print("\n\n=== SENSITIVITY ===")
    inst = generate_instance("MC-CSSP-M", N=40, K=15, seed=123)
    rows = []

    for eta in [0.0, 0.15, 0.30, 0.45, 0.60]:
        for s in range(8):
            r = run_qiddm(inst, pop_size=POP, generations=GENS,
                          eta_interference=eta, seed=s)
            rows.append(dict(param="eta", value=eta, run=s, utility=r["utility"]))

    for tmax_mult in [0.5, 0.75, 1.0, 1.5, 2.0]:
        for s in range(8):
            r = run_qiddm(inst, pop_size=POP, generations=GENS,
                          theta_max=tmax_mult * 0.10 * np.pi, seed=s)
            rows.append(dict(param="theta_max", value=tmax_mult, run=s,
                             utility=r["utility"]))

    for decay in [1.0, 2.0, 3.0, 5.0, 8.0]:
        for s in range(8):
            r = run_qiddm(inst, pop_size=POP, generations=GENS,
                          decay=decay, seed=s)
            rows.append(dict(param="decay", value=decay, run=s,
                             utility=r["utility"]))

    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(RES_DIR, "sensitivity_per_run.csv"), index=False)
    agg = df.groupby(["param", "value"]).agg(
        util_mean=("utility", "mean"), util_std=("utility", "std")).round(4).reset_index()
    agg.to_csv(os.path.join(RES_DIR, "sensitivity_summary.csv"), index=False)
    print(agg.to_string(index=False))
    return agg


# ------------------------------------------------------------------ #
def stat_tests():
    print("\n\n=== STATISTICAL TESTS ===")
    df = pd.read_csv(os.path.join(RES_DIR, "main_per_run.csv"))
    rows = []
    for inst in df.instance.unique():
        sub = df[df.instance == inst]
        q = sub[sub.method == "QIDDM"].utility.values
        for m in ["GA", "PSO", "QEA"]:
            v = sub[sub.method == m].utility.values
            if len(v) >= 3 and len(q) >= 3:
                u, p = stats.mannwhitneyu(q, v, alternative="greater")
                # Cliff's delta (effect size)
                gt = sum(qi > vi for qi in q for vi in v)
                lt = sum(qi < vi for qi in q for vi in v)
                cliff = (gt - lt) / (len(q) * len(v))
                rows.append(dict(instance=inst, qiddm_vs=m,
                                 qiddm_mean=q.mean(), other_mean=v.mean(),
                                 U=u, p_value=p,
                                 cliff_delta=cliff,
                                 effect_magnitude=_cliff_label(cliff),
                                 significant=p < 0.05))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES_DIR, "stat_tests.csv"), index=False)
    print(out.to_string(index=False))

    # Friedman test across stochastic methods (excluding deterministic)
    methods = ["GA", "PSO", "QEA", "QIDDM"]
    friedman_rows = []
    for inst in df.instance.unique():
        sub = df[(df.instance == inst) & (df.method.isin(methods))]
        if sub.run.nunique() < 3:
            continue
        # build matrix runs x methods
        pivot = sub.pivot_table(index="run", columns="method", values="utility")
        if pivot.shape[1] != len(methods) or pivot.isnull().any().any():
            continue
        st, p = stats.friedmanchisquare(*[pivot[m].values for m in methods])
        friedman_rows.append(dict(instance=inst, statistic=st, p_value=p,
                                  significant=p < 0.05))
    pd.DataFrame(friedman_rows).to_csv(
        os.path.join(RES_DIR, "friedman_tests.csv"), index=False)
    print(pd.DataFrame(friedman_rows).to_string(index=False))


def _cliff_label(d):
    a = abs(d)
    if a < 0.147: return "negligible"
    if a < 0.33:  return "small"
    if a < 0.474: return "medium"
    return "large"


# ------------------------------------------------------------------ #
if __name__ == "__main__":
    main_comparison()
    ablation_study()
    sensitivity_study()
    stat_tests()
    print("\nALL EXPERIMENTS COMPLETE")

"""
Comparative experiment: QIDDM vs TOPSIS, AHP, GA, PSO
on three MC-CSSP instances of increasing size.

Metrics collected per (algorithm, instance, run):
  - utility            (solution quality)
  - cpu_time           (seconds)
  - iterations_to_best (convergence speed; analytic methods = 0)
  - feasibility (capacity slack)

Outputs:
  results/summary_table.csv
  results/per_run_table.csv
  results/convergence_data.npz
"""

from __future__ import annotations
import os
import sys
import numpy as np
import pandas as pd

# allow running from either project root or experiments/ folder
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from benchmarks.problem import generate_instance
from algorithms.baselines import run_topsis, run_ahp, run_ga, run_pso
from algorithms.qiddm import run_qiddm


INSTANCES = [
    dict(name="MC-CSSP-S",  N=20, K=8,  seed=42),
    dict(name="MC-CSSP-M",  N=40, K=15, seed=123),
    dict(name="MC-CSSP-L",  N=80, K=30, seed=2026),
]

METAHEURISTIC_RUNS = 20    # stochastic methods get 20 independent runs
GENERATIONS = 120
POP_SIZE = 40


def iterations_to_best(history) -> int:
    if not history:
        return 0
    best = max(history)
    for i, v in enumerate(history):
        if abs(v - best) < 1e-9:
            return i
    return len(history) - 1


def run_all():
    per_run_rows = []
    convergence_store = {}

    for cfg in INSTANCES:
        inst = generate_instance(cfg["name"], N=cfg["N"], K=cfg["K"], seed=cfg["seed"])
        print(f"\n=== {inst.name}  (N={inst.N}, K={inst.K}) ===")

        # Deterministic methods — single run
        for fn, label in [(run_topsis, "TOPSIS"), (run_ahp, "AHP")]:
            r = fn(inst)
            per_run_rows.append(dict(
                instance=inst.name, method=label, run=0,
                utility=r["utility"], cpu_time=r["cpu_time"],
                iterations_to_best=0,
                cost=r["detail"]["cost"], quality=r["detail"]["quality"],
                lead_time=r["detail"]["lead_time"], reliability=r["detail"]["reliability"],
                capacity_slack=r["detail"]["capacity_slack"]))
            convergence_store[(inst.name, label, 0)] = np.array(r["convergence"])
            print(f"  {label:7s}  util={r['utility']:.4f}  t={r['cpu_time']:.4f}s")

        # Stochastic methods — multi-run
        for fn, label in [(run_ga, "GA"), (run_pso, "PSO"), (run_qiddm, "QIDDM")]:
            print(f"  {label:7s}", end=" ", flush=True)
            for run_idx in range(METAHEURISTIC_RUNS):
                kwargs = dict(seed=run_idx)
                if label == "GA":
                    r = fn(inst, pop_size=POP_SIZE, generations=GENERATIONS, **kwargs)
                elif label == "PSO":
                    r = fn(inst, swarm=POP_SIZE, iters=GENERATIONS, **kwargs)
                else:
                    r = fn(inst, pop_size=POP_SIZE, generations=GENERATIONS, **kwargs)
                per_run_rows.append(dict(
                    instance=inst.name, method=label, run=run_idx,
                    utility=r["utility"], cpu_time=r["cpu_time"],
                    iterations_to_best=iterations_to_best(r["convergence"]),
                    cost=r["detail"]["cost"], quality=r["detail"]["quality"],
                    lead_time=r["detail"]["lead_time"], reliability=r["detail"]["reliability"],
                    capacity_slack=r["detail"]["capacity_slack"]))
                convergence_store[(inst.name, label, run_idx)] = np.array(r["convergence"])
                print(".", end="", flush=True)
            print()

    df = pd.DataFrame(per_run_rows)
    out_dir = os.path.join(ROOT, "results")
    os.makedirs(out_dir, exist_ok=True)
    df.to_csv(os.path.join(out_dir, "per_run_table.csv"), index=False)

    # Aggregate summary
    agg = df.groupby(["instance", "method"]).agg(
        util_mean=("utility", "mean"),
        util_std=("utility", "std"),
        util_best=("utility", "max"),
        cpu_mean=("cpu_time", "mean"),
        iter_mean=("iterations_to_best", "mean"),
        cost_mean=("cost", "mean"),
        quality_mean=("quality", "mean"),
        lead_time_mean=("lead_time", "mean"),
        reliability_mean=("reliability", "mean"),
    ).round(4).reset_index()
    agg.to_csv(os.path.join(out_dir, "summary_table.csv"), index=False)
    print("\nSummary written to results/summary_table.csv")
    print(agg.to_string(index=False))

    # Save convergence
    np.savez_compressed(
        os.path.join(out_dir, "convergence_data.npz"),
        **{f"{k[0]}__{k[1]}__{k[2]}": v for k, v in convergence_store.items()})
    print("Convergence data saved to results/convergence_data.npz")
    return df, agg


if __name__ == "__main__":
    run_all()

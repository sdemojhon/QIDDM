"""
Generate publication-ready figures and statistical tests:
  - fig_convergence_<instance>.png
  - fig_utility_box.png
  - fig_runtime_bar.png
  - fig_radar.png            (criteria profile of best solution per method)
  - fig_iter_to_best.png
  - significance_wilcoxon.csv
"""

from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "legend.fontsize": 10,
    "figure.dpi": 130,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
})

COLORS = {"TOPSIS": "#888888", "AHP": "#bf6b6b", "GA": "#4c72b0",
          "PSO": "#55a868", "QIDDM": "#d6201f"}
ORDER = ["TOPSIS", "AHP", "GA", "PSO", "QIDDM"]

df = pd.read_csv(os.path.join(RES, "per_run_table.csv"))
conv = np.load(os.path.join(RES, "convergence_data.npz"))
instances = list(df.instance.unique())


# --------------------------------------------------------------------- 1
def plot_convergence():
    fig, axes = plt.subplots(1, len(instances), figsize=(15, 4.2), sharey=False)
    for ax, inst in zip(axes, instances):
        for method in ORDER:
            keys = [k for k in conv.files if k.startswith(f"{inst}__{method}__")]
            if not keys:
                continue
            curves = np.array([conv[k] for k in keys])
            mean = curves.mean(axis=0)
            std = curves.std(axis=0)
            x = np.arange(len(mean))
            ax.plot(x, mean, label=method, color=COLORS[method],
                    linewidth=2 if method == "QIDDM" else 1.4,
                    linestyle="-" if method in ("GA", "PSO", "QIDDM") else "--")
            if curves.shape[0] > 1:
                ax.fill_between(x, mean - std, mean + std,
                                color=COLORS[method], alpha=0.12)
        ax.set_title(f"Convergence — {inst}")
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Best utility")
        ax.grid(alpha=0.3)
    axes[-1].legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_convergence.png"))
    plt.close(fig)


# --------------------------------------------------------------------- 2
def plot_utility_box():
    fig, axes = plt.subplots(1, len(instances), figsize=(14, 4.2), sharey=False)
    for ax, inst in zip(axes, instances):
        sub = df[df.instance == inst]
        data, labels, colors = [], [], []
        for m in ORDER:
            vals = sub[sub.method == m].utility.values
            if len(vals) == 0:
                continue
            data.append(vals if len(vals) > 1 else np.repeat(vals, 5))
            labels.append(m)
            colors.append(COLORS[m])
        bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c)
            patch.set_alpha(0.55)
        for med in bp["medians"]:
            med.set_color("black")
        ax.set_title(f"Utility distribution — {inst}")
        ax.set_ylabel("Utility")
        ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_utility_box.png"))
    plt.close(fig)


# --------------------------------------------------------------------- 3
def plot_runtime():
    agg = df.groupby(["instance", "method"]).cpu_time.mean().reset_index()
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    width = 0.16
    x = np.arange(len(instances))
    for i, m in enumerate(ORDER):
        vals = [agg[(agg.instance == inst) & (agg.method == m)].cpu_time.values
                for inst in instances]
        vals = [v[0] if len(v) else 0 for v in vals]
        ax.bar(x + (i - 2) * width, vals, width, label=m, color=COLORS[m])
    ax.set_xticks(x)
    ax.set_xticklabels(instances)
    ax.set_ylabel("Mean CPU time (s)")
    ax.set_title("Runtime comparison")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_runtime_bar.png"))
    plt.close(fig)


# --------------------------------------------------------------------- 4
def plot_iter_to_best():
    sub = df[df.method.isin(["GA", "PSO", "QIDDM"])]
    agg = sub.groupby(["instance", "method"]).iterations_to_best.mean().reset_index()
    fig, ax = plt.subplots(figsize=(7.5, 4.0))
    width = 0.25
    x = np.arange(len(instances))
    for i, m in enumerate(["GA", "PSO", "QIDDM"]):
        vals = [agg[(agg.instance == inst) & (agg.method == m)]
                .iterations_to_best.values for inst in instances]
        vals = [v[0] if len(v) else 0 for v in vals]
        ax.bar(x + (i - 1) * width, vals, width, label=m, color=COLORS[m])
    ax.set_xticks(x)
    ax.set_xticklabels(instances)
    ax.set_ylabel("Mean iterations to best (lower = faster)")
    ax.set_title("Convergence speed")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_iter_to_best.png"))
    plt.close(fig)


# --------------------------------------------------------------------- 5
def plot_radar():
    """Radar chart of best solution criteria for each method on the largest instance."""
    inst = "MC-CSSP-L"
    sub = df[df.instance == inst]
    metrics = ["cost", "quality", "lead_time", "reliability"]
    # invert cost & lead_time so larger = better
    rows = {}
    for m in ORDER:
        v = sub[sub.method == m]
        if len(v) == 0:
            continue
        best_row = v.loc[v.utility.idxmax()]
        rows[m] = [best_row.cost, best_row.quality, best_row.lead_time, best_row.reliability]
    arr = np.array([rows[m] for m in rows.keys()])

    norm = np.zeros_like(arr)
    for j, met in enumerate(metrics):
        col = arr[:, j]
        rng = col.max() - col.min() + 1e-12
        if met in ("cost", "lead_time"):
            norm[:, j] = (col.max() - col) / rng
        else:
            norm[:, j] = (col - col.min()) / rng

    angles = np.linspace(0, 2 * np.pi, len(metrics), endpoint=False).tolist()
    angles += angles[:1]
    fig = plt.figure(figsize=(6.0, 6.0))
    ax = plt.subplot(111, polar=True)
    for i, m in enumerate(rows.keys()):
        vals = norm[i].tolist() + [norm[i, 0]]
        ax.plot(angles, vals, color=COLORS[m], linewidth=2,
                label=m, linestyle="-" if m == "QIDDM" else "--")
        ax.fill(angles, vals, color=COLORS[m], alpha=0.10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["Cost\n(lower)", "Quality", "Lead time\n(lower)", "Reliability"])
    ax.set_yticklabels([])
    ax.set_title(f"Criteria profile of best solutions ({inst})", pad=18)
    ax.legend(loc="upper right", bbox_to_anchor=(1.30, 1.10))
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_radar.png"))
    plt.close(fig)


# --------------------------------------------------------------------- 6
def wilcoxon_tests():
    """Pairwise Wilcoxon rank-sum vs QIDDM for stochastic methods."""
    rows = []
    for inst in instances:
        sub = df[df.instance == inst]
        q = sub[sub.method == "QIDDM"].utility.values
        for m in ["GA", "PSO"]:
            v = sub[sub.method == m].utility.values
            if len(v) < 3 or len(q) < 3:
                continue
            stat, p = stats.mannwhitneyu(q, v, alternative="greater")
            rows.append(dict(instance=inst, qiddm_vs=m,
                             qiddm_mean=q.mean(), other_mean=v.mean(),
                             U=stat, p_value=p,
                             significant_005=p < 0.05))
    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(RES, "significance_wilcoxon.csv"), index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    plot_convergence()
    plot_utility_box()
    plot_runtime()
    plot_iter_to_best()
    plot_radar()
    wilcoxon_tests()
    print("\nFigures + significance tests written to results/")

"""
Generate publication-ready figures for the extended QIDDM paper:

  fig_convergence.png     — main convergence (5 instances)
  fig_utility_box.png     — distribution of utilities
  fig_runtime_bar.png     — runtime per instance
  fig_iter_to_best.png    — convergence speed
  fig_radar.png           — multi-criteria profile
  fig_ablation.png        — ablation study bar chart
  fig_scaling.png         — utility & CPU vs N
  fig_sensitivity.png     — eta / theta_max / decay sweeps
  fig_optimality_gap.png  — vs EXACT optimum on small instance
  graphical_abstract.png  — single-panel summary
"""

from __future__ import annotations
import os, sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patches as mpatches

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
RES = os.path.join(ROOT, "results")
os.makedirs(RES, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "axes.titlesize": 11,
    "axes.labelsize": 10.5,
    "legend.fontsize": 9.5,
    "figure.dpi": 130,
    "savefig.dpi": 220,
    "savefig.bbox": "tight",
})

COLORS = {
    "TOPSIS": "#888888", "AHP": "#bf6b6b", "GA": "#4c72b0",
    "PSO": "#55a868", "QEA": "#9467bd", "QIDDM": "#d6201f",
    "EXACT": "#000000",
    "QIDDM-full": "#d6201f", "QIDDM-noDyn": "#fb8072",
    "QIDDM-noInt": "#fdb462", "QIDDM-noLS": "#80b1d3",
    "QIDDM-noWarm": "#bebada",
}
ORDER_MAIN = ["TOPSIS", "AHP", "GA", "PSO", "QEA", "QIDDM", "EXACT"]
ORDER_ABL = ["QIDDM-full", "QIDDM-noDyn", "QIDDM-noInt", "QIDDM-noLS", "QIDDM-noWarm"]


def load_main():
    df = pd.read_csv(os.path.join(RES, "main_per_run.csv"))
    conv = np.load(os.path.join(RES, "main_convergence.npz"))
    return df, conv


def plot_convergence():
    df, conv = load_main()
    instances = list(df.instance.unique())
    n = len(instances)
    cols = min(n, 3)
    rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5.0 * cols, 3.7 * rows),
                              squeeze=False)
    for idx, inst in enumerate(instances):
        ax = axes[idx // cols, idx % cols]
        for m in ORDER_MAIN:
            keys = [k for k in conv.files if k.startswith(f"{inst}__{m}__")]
            if not keys:
                continue
            curves = [conv[k] for k in keys]
            # Pad to common length
            mx = max(len(c) for c in curves)
            curves = np.array([np.pad(c, (0, mx - len(c)), constant_values=c[-1])
                               for c in curves])
            mean = curves.mean(axis=0)
            ax.plot(np.arange(mx), mean, label=m, color=COLORS[m],
                    linewidth=2.2 if m == "QIDDM" else 1.3,
                    linestyle="-" if m in ("GA", "PSO", "QEA", "QIDDM") else "--")
            if curves.shape[0] > 1:
                std = curves.std(axis=0)
                ax.fill_between(np.arange(mx), mean - std, mean + std,
                                color=COLORS[m], alpha=0.10)
        ax.set_title(inst)
        ax.set_xlabel("Iteration")
        ax.set_ylabel("Best utility")
        ax.grid(alpha=0.3)
        if idx == 0:
            ax.legend(loc="lower right", fontsize=8.5)
    # hide empty axes
    for k in range(idx + 1, rows * cols):
        axes[k // cols, k % cols].axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_convergence.png"))
    plt.close(fig)


def plot_utility_box():
    df, _ = load_main()
    instances = list(df.instance.unique())
    n = len(instances); cols = min(n, 3); rows = int(np.ceil(n / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(4.6 * cols, 3.6 * rows),
                              squeeze=False)
    for idx, inst in enumerate(instances):
        ax = axes[idx // cols, idx % cols]
        sub = df[df.instance == inst]
        data, labels, colors = [], [], []
        for m in ORDER_MAIN:
            v = sub[sub.method == m].utility.values
            if len(v) == 0:
                continue
            data.append(v if len(v) > 1 else np.repeat(v, 5))
            labels.append(m); colors.append(COLORS[m])
        bp = ax.boxplot(data, tick_labels=labels, patch_artist=True, widths=0.6)
        for patch, c in zip(bp["boxes"], colors):
            patch.set_facecolor(c); patch.set_alpha(0.55)
        for med in bp["medians"]:
            med.set_color("black")
        ax.set_title(inst); ax.set_ylabel("Utility")
        ax.tick_params(axis="x", rotation=30)
        ax.grid(alpha=0.3, axis="y")
    for k in range(idx + 1, rows * cols):
        axes[k // cols, k % cols].axis("off")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_utility_box.png"))
    plt.close(fig)


def plot_runtime():
    df, _ = load_main()
    instances = list(df.instance.unique())
    agg = df.groupby(["instance", "method"]).cpu_time.mean().reset_index()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    width = 0.13
    x = np.arange(len(instances))
    methods = [m for m in ORDER_MAIN if m != "EXACT"]
    for i, m in enumerate(methods):
        vals = []
        for inst in instances:
            v = agg[(agg.instance == inst) & (agg.method == m)].cpu_time.values
            vals.append(v[0] if len(v) else 0)
        ax.bar(x + (i - len(methods) / 2) * width, vals, width,
               label=m, color=COLORS[m])
    ax.set_xticks(x); ax.set_xticklabels(instances, rotation=20)
    ax.set_ylabel("Mean CPU time (s)")
    ax.set_title("Runtime comparison")
    ax.set_yscale("log")
    ax.legend(ncol=3, fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_runtime_bar.png"))
    plt.close(fig)


def plot_iter_to_best():
    df, _ = load_main()
    instances = list(df.instance.unique())
    sub = df[df.method.isin(["GA", "PSO", "QEA", "QIDDM"])]
    agg = sub.groupby(["instance", "method"]).iterations_to_best.mean().reset_index()
    fig, ax = plt.subplots(figsize=(8.5, 4.0))
    width = 0.18
    x = np.arange(len(instances))
    methods = ["GA", "PSO", "QEA", "QIDDM"]
    for i, m in enumerate(methods):
        vals = [agg[(agg.instance == inst) & (agg.method == m)]
                .iterations_to_best.values for inst in instances]
        vals = [v[0] if len(v) else 0 for v in vals]
        ax.bar(x + (i - 1.5) * width, vals, width, label=m, color=COLORS[m])
    ax.set_xticks(x); ax.set_xticklabels(instances, rotation=20)
    ax.set_ylabel("Mean iterations to best (lower = faster)")
    ax.set_title("Convergence speed")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_iter_to_best.png"))
    plt.close(fig)


def plot_radar(target_instance="MC-CSSP-L"):
    df, _ = load_main()
    sub = df[df.instance == target_instance]
    metrics = ["cost", "quality", "lead_time", "reliability"]
    rows = {}
    for m in ORDER_MAIN:
        v = sub[sub.method == m]
        if len(v) == 0:
            continue
        best = v.loc[v.utility.idxmax()]
        rows[m] = [best.cost, best.quality, best.lead_time, best.reliability]
    if not rows:
        return
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
    fig = plt.figure(figsize=(6.4, 6.4))
    ax = plt.subplot(111, polar=True)
    for i, m in enumerate(rows.keys()):
        vals = norm[i].tolist() + [norm[i, 0]]
        lw = 2.4 if m == "QIDDM" else 1.4
        ax.plot(angles, vals, color=COLORS[m], linewidth=lw,
                label=m, linestyle="-" if m == "QIDDM" else "--")
        ax.fill(angles, vals, color=COLORS[m], alpha=0.10)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(["Cost\n(lower)", "Quality", "Lead time\n(lower)", "Reliability"])
    ax.set_yticklabels([])
    ax.set_title(f"Criteria profile — {target_instance}", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.32, 1.10), fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_radar.png"))
    plt.close(fig)


def plot_ablation():
    path = os.path.join(RES, "ablation_summary.csv")
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    instances = list(df.instance.unique())
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    width = 0.14
    x = np.arange(len(instances))
    for i, m in enumerate(ORDER_ABL):
        vals = [df[(df.instance == inst) & (df.method == m)].util_mean.values
                for inst in instances]
        errs = [df[(df.instance == inst) & (df.method == m)].util_std.values
                for inst in instances]
        vals = [v[0] if len(v) else 0 for v in vals]
        errs = [e[0] if len(e) else 0 for e in errs]
        ax.bar(x + (i - 2) * width, vals, width, yerr=errs, capsize=3,
               label=m, color=COLORS[m])
    ax.set_xticks(x); ax.set_xticklabels(instances)
    ax.set_ylabel("Mean utility (± std)")
    ax.set_title("Ablation: contribution of each QIDDM component")
    ax.legend(ncol=3, fontsize=9)
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_ablation.png"))
    plt.close(fig)


def plot_scaling():
    df, _ = load_main()
    # Map instance to N
    N_map = {"MC-CSSP-S": 20, "MC-CSSP-M": 40, "MC-CSSP-L": 80,
             "MC-CSSP-XL": 200, "MC-CSSP-RW": 30}
    df["N"] = df.instance.map(N_map)
    df = df[df.N.notna()].copy()

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for m in ["GA", "PSO", "QEA", "QIDDM", "AHP", "TOPSIS"]:
        sub = df[df.method == m].groupby("N").agg(
            util=("utility", "mean"), cpu=("cpu_time", "mean")).reset_index()
        sub = sub.sort_values("N")
        if len(sub) == 0:
            continue
        lw = 2.2 if m == "QIDDM" else 1.3
        axes[0].plot(sub.N, sub.util, marker="o", color=COLORS[m],
                     label=m, linewidth=lw)
        axes[1].plot(sub.N, sub.cpu, marker="o", color=COLORS[m],
                     label=m, linewidth=lw)
    axes[0].set_xlabel("Problem size N"); axes[0].set_ylabel("Mean utility")
    axes[0].set_title("Solution quality vs problem size")
    axes[0].grid(alpha=0.3); axes[0].legend(fontsize=9)
    axes[1].set_xlabel("Problem size N"); axes[1].set_ylabel("Mean CPU time (s)")
    axes[1].set_title("Runtime scaling")
    axes[1].set_yscale("log")
    axes[1].grid(alpha=0.3); axes[1].legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_scaling.png"))
    plt.close(fig)


def plot_sensitivity():
    path = os.path.join(RES, "sensitivity_summary.csv")
    if not os.path.exists(path):
        return
    df = pd.read_csv(path)
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    for ax, p in zip(axes, ["eta", "theta_max", "decay"]):
        sub = df[df.param == p].sort_values("value")
        ax.errorbar(sub["value"], sub["util_mean"], yerr=sub["util_std"],
                    marker="o", linewidth=2, capsize=4, color=COLORS["QIDDM"])
        ax.set_xlabel({"eta": "η (interference strength)",
                       "theta_max": "θ_max multiplier",
                       "decay": "decay λ"}[p])
        ax.set_ylabel("Mean utility")
        ax.set_title(f"Sensitivity to {p}")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_sensitivity.png"))
    plt.close(fig)


def plot_optimality_gap():
    df, _ = load_main()
    sub = df[df.instance == "MC-CSSP-S"]
    if "EXACT" not in sub.method.values:
        return
    opt = sub[sub.method == "EXACT"].utility.iloc[0]
    rows = []
    for m in ORDER_MAIN:
        if m == "EXACT": continue
        v = sub[sub.method == m].utility.values
        if len(v) == 0: continue
        gap_mean = (opt - v.mean()) / opt * 100
        gap_best = (opt - v.max()) / opt * 100
        rows.append((m, gap_mean, gap_best))
    fig, ax = plt.subplots(figsize=(7.5, 4))
    ms = [r[0] for r in rows]
    means = [r[1] for r in rows]
    bests = [r[2] for r in rows]
    x = np.arange(len(ms))
    ax.bar(x - 0.2, means, 0.4, label="Mean gap (%)",
           color=[COLORS[m] for m in ms], alpha=0.7)
    ax.bar(x + 0.2, bests, 0.4, label="Best-of-runs gap (%)",
           color=[COLORS[m] for m in ms], alpha=1.0,
           edgecolor="black", linewidth=1.2)
    ax.set_xticks(x); ax.set_xticklabels(ms)
    ax.set_ylabel("Optimality gap vs EXACT (%)")
    ax.set_title(f"Optimality gap on MC-CSSP-S (EXACT optimum = {opt:.4f})")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout()
    fig.savefig(os.path.join(RES, "fig_optimality_gap.png"))
    plt.close(fig)


def graphical_abstract():
    """Single-panel summary of QIDDM core idea + result."""
    df, _ = load_main()
    fig = plt.figure(figsize=(11, 5.2))
    gs = fig.add_gridspec(2, 3, hspace=0.55, wspace=0.45,
                          width_ratios=[1.1, 1.0, 1.2])

    # Panel A: concept diagram
    axA = fig.add_subplot(gs[:, 0])
    axA.set_xlim(0, 10); axA.set_ylim(0, 10); axA.axis("off")
    axA.set_title("(A)  QIDDM concept", fontsize=12, fontweight="bold", loc="left")
    boxes = [
        (0.5, 7.5, "Q-bit population\n(superposition)", "#fde2e2"),
        (0.5, 5.0, "Dynamic phase\nrotation gate", "#cfe2f3"),
        (0.5, 2.5, "Multi-criteria\ninterference", "#d9ead3"),
        (0.5, 0.0, "Decision-aware\nlocal search", "#fff2cc"),
    ]
    for x, y, txt, col in boxes:
        b = FancyBboxPatch((x, y), 8.5, 1.7, boxstyle="round,pad=0.1",
                           facecolor=col, edgecolor="#333", linewidth=1.2)
        axA.add_patch(b)
        axA.text(x + 4.25, y + 0.85, txt, ha="center", va="center", fontsize=10)
    # arrows
    for y in (7.3, 4.8, 2.3):
        axA.annotate("", xy=(4.75, y), xytext=(4.75, y + 0.3),
                     arrowprops=dict(arrowstyle="->", lw=1.2))

    # Panel B: utility comparison on largest instance
    axB = fig.add_subplot(gs[0, 1])
    axB.set_title("(B)  Best utility (MC-CSSP-L)", fontsize=11, loc="left")
    sub = df[df.instance == "MC-CSSP-L"].groupby("method").utility.mean()
    methods = [m for m in ["TOPSIS", "AHP", "GA", "PSO", "QEA", "QIDDM"]
               if m in sub.index]
    vals = [sub[m] for m in methods]
    bars = axB.bar(methods, vals, color=[COLORS[m] for m in methods])
    axB.set_ylabel("Mean utility")
    axB.tick_params(axis="x", rotation=30)
    axB.grid(alpha=0.3, axis="y")
    # highlight QIDDM
    for bar, m in zip(bars, methods):
        if m == "QIDDM":
            bar.set_edgecolor("black"); bar.set_linewidth(1.8)

    # Panel C: convergence speed
    axC = fig.add_subplot(gs[1, 1])
    axC.set_title("(C)  Iterations to best", fontsize=11, loc="left")
    sub = df[(df.instance == "MC-CSSP-L") &
             (df.method.isin(["GA", "PSO", "QEA", "QIDDM"]))]
    agg = sub.groupby("method").iterations_to_best.mean()
    ms = [m for m in ["GA", "PSO", "QEA", "QIDDM"] if m in agg.index]
    bars = axC.bar(ms, [agg[m] for m in ms], color=[COLORS[m] for m in ms])
    axC.set_ylabel("Iter. to best")
    axC.tick_params(axis="x", rotation=20)
    axC.grid(alpha=0.3, axis="y")
    for bar, m in zip(bars, ms):
        if m == "QIDDM":
            bar.set_edgecolor("black"); bar.set_linewidth(1.8)

    # Panel D: scaling
    axD = fig.add_subplot(gs[:, 2])
    axD.set_title("(D)  Scaling: utility vs problem size N",
                  fontsize=11, loc="left")
    N_map = {"MC-CSSP-S": 20, "MC-CSSP-M": 40, "MC-CSSP-L": 80,
             "MC-CSSP-XL": 200, "MC-CSSP-RW": 30}
    df2 = df.copy(); df2["N"] = df2.instance.map(N_map)
    for m in ["AHP", "TOPSIS", "GA", "PSO", "QEA", "QIDDM"]:
        s = df2[df2.method == m].groupby("N").utility.mean().sort_index()
        if len(s) == 0: continue
        lw = 2.6 if m == "QIDDM" else 1.4
        axD.plot(s.index, s.values, marker="o", color=COLORS[m],
                 linewidth=lw, label=m,
                 markersize=8 if m == "QIDDM" else 5)
    axD.set_xlabel("N (candidate suppliers)")
    axD.set_ylabel("Mean utility")
    axD.legend(fontsize=9, loc="lower right")
    axD.grid(alpha=0.3)

    fig.suptitle("Quantum-Inspired Dynamic Decision-Making (QIDDM)",
                 fontsize=14, fontweight="bold", y=1.01)
    fig.savefig(os.path.join(RES, "graphical_abstract.png"),
                dpi=240, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    plot_convergence()
    plot_utility_box()
    plot_runtime()
    plot_iter_to_best()
    plot_radar()
    plot_ablation()
    plot_scaling()
    plot_sensitivity()
    plot_optimality_gap()
    graphical_abstract()
    print("All figures saved to results/")

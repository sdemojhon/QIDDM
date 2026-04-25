# QIDDM — Quantum-Inspired Dynamic Decision-Making

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![NumPy](https://img.shields.io/badge/numpy-2.x-blue.svg)](https://numpy.org/)
[![SciPy](https://img.shields.io/badge/scipy-1.17-blue.svg)](https://scipy.org/)
[![Reproducible](https://img.shields.io/badge/reproducible-yes-brightgreen.svg)](#reproducing-every-result)
[![Paper](https://img.shields.io/badge/paper-Q1%20submission-red.svg)](paper/QIDDM_paper_v3.docx)

> **A superposition-based framework for multi-criteria capacitated supplier selection.**
> Code, data, figures and statistical tests for the QIDDM paper — fully reproducible from fixed seeds.

---

## ✨ Highlights

- 🔬 Novel quantum-inspired metaheuristic with **adaptive phase rotation** and **criteria-aware interference modulation**
- 📊 **5 benchmark instances** (N = 20, 30, 40, 80, 200) including a real-world-correlated panel
- ⚖️ **6 baselines**: TOPSIS, AHP, GA, PSO, canonical Han–Kim QEA, exact enumeration upper bound
- 📈 **Full statistical analysis**: Mann–Whitney U, Friedman, Cliff's δ effect size
- 🧪 **Ablation + sensitivity studies** isolating every component contribution
- 🌍 Aligned with **United Nations SDG 9 and SDG 12.5** (resilient & responsible production)

---

## 🏆 Headline Results

| Metric | QIDDM | Best Baseline | Improvement |
|---|---|---|---|
| Optimality gap on small instance (best of 20) | **0.00 %** (= EXACT optimum) | 0.17 % (PSO) | ✅ |
| Mean utility on MC-CSSP-L (N = 80) | **0.6792** | 0.6713 (TOPSIS) | +1.2 % |
| Mean utility on MC-CSSP-XL (N = 200) | **0.6803** | 0.6808 (AHP) | tied; best-run 0.6889 |
| Iterations to best (MC-CSSP-L) | **24.8** | 61.7 (GA) | **2.5× faster** |
| Run-to-run variance σ | **≤ 0.0025** | ≥ 0.005 | ⬇ |
| Cliff's δ vs GA / PSO / QEA on M / L / XL | **1.000** (perfect dominance) | – | ⭐ |
| p-value (Mann–Whitney U) | **< 10⁻⁷** on all non-trivial instances | – | ⭐ |

---

## 📁 Repository Layout

```
qiddm-paper/
├── benchmarks/
│   ├── problem.py             # MC-CSSP synthetic generator (with synergy / risk)
│   └── realworld.py           # Real-world-correlated supplier instance
├── algorithms/
│   ├── baselines.py           # TOPSIS, AHP, GA, PSO
│   ├── extra_baselines.py     # Han-Kim QEA, EXACT enumeration
│   ├── qiddm.py               # ⭐ Proposed QIDDM (vectorised rotation gate)
│   └── qiddm_ablation.py      # Ablation variants (no-Dyn / no-Int / no-LS / no-Warm)
├── experiments/
│   ├── run_full_experiment.py # Main + ablation + sensitivity + statistical tests
│   └── make_full_plots.py     # 9 figures + graphical abstract
├── results/                   # All CSVs, PNGs and convergence NPZ
├── paper/
│   ├── QIDDM_paper_v3.docx    # Main manuscript (Q1 submission)
│   ├── Cover_Letter.docx      # Cover letter
│   └── Supplementary_Material.docx
└── README.md
```

---

## ⚡ Quick Start

```bash
git clone https://github.com/<owner>/qiddm-paper.git
cd qiddm-paper

# 1. Install dependencies
pip install numpy pandas scipy matplotlib python-docx openpyxl

# 2. Run the entire experimental suite (≈ 15–25 min on a single CPU thread)
python experiments/run_full_experiment.py

# 3. Regenerate every figure and the graphical abstract
python experiments/make_full_plots.py

# 4. (optional) Rebuild the paper Word document
python paper/build_paper_v3.py
```

All random seeds are fixed (`0–19` for stochastic methods; instance-specific seeds documented in `benchmarks/problem.py`). Output is byte-identical across runs.

---

## 🔬 Reproducing Every Result

| Result | Command | Output |
|---|---|---|
| Table 1 (main summary) | `python experiments/run_full_experiment.py` | `results/main_summary.csv` |
| Table 2 (Mann–Whitney U + Cliff's δ) | (above) | `results/stat_tests.csv` |
| Table 3 (Friedman test) | (above) | `results/friedman_tests.csv` |
| Table 4 (ablation) | (above) | `results/ablation_summary.csv` |
| Figures 1–9 + graphical abstract | `python experiments/make_full_plots.py` | `results/*.png` |

---

## 🧠 Method Summary

QIDDM represents each candidate decision as a vector of **quantum bits** in superposition:

```
|ψ_i⟩ = α_i |0⟩ + β_i |1⟩,   |α_i|² + |β_i|² = 1,
P(select position i) = |β_i|²
```

The population evolves through a **dynamic phase-rotation gate**:

```
θ_t = θ_max · exp(-λ t / T) + θ_min + ½ θ_max · 𝟙[stagnation > 5]
```

modulated by a **multi-criteria interference vector**:

```
phase_eff = θ_t · (1 + η · I_j),   I_j ∈ [-1, 1]
```

with periodic **criteria-guided 1-swap local search** every L iterations. See Section 4 of the paper for the full pseudocode and complexity analysis.

---

## 📚 Citation

If you use QIDDM, the MC-CSSP benchmark, or any of the figures in academic work, please cite:

```bibtex
@article{qiddm2026,
  title   = {Quantum-Inspired Dynamic Decision-Making (QIDDM):
             A Superposition-Based Framework for Multi-Criteria
             Capacitated Supplier Selection},
  author  = {[Author Name] and [Co-Author Name]},
  journal = {Nexus of Research Horizon},
  year    = {2026},
  note    = {Code: \url{https://github.com/<owner>/qiddm-paper}}
}
```

---

## 🤝 Contributing

Contributions, bug reports and suggestions are welcome via [Issues](https://github.com/<owner>/qiddm-paper/issues) and [Pull Requests](https://github.com/<owner>/qiddm-paper/pulls).

---

## 📄 License

Released under the **MIT License** — see [`LICENSE`](LICENSE) for full text.

---

## 📬 Contact

- **Corresponding author:** [Author Name] — corresponding@institution.edu
- **ORCID:** 0000-0000-0000-0000

---

<sub>Last update: April 2026 · Code version: v3.0 · Paper version: v3</sub>

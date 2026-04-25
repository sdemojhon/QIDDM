"""
QIDDM ablation variants for component-contribution analysis:

  QIDDM-noDyn   : remove dynamic rotation schedule (use constant theta)
  QIDDM-noInt   : remove multi-criteria interference modulation (eta=0)
  QIDDM-noLS    : remove decision-aware local search
  QIDDM-noWarm  : remove multi-criteria warm start (uniform 1/sqrt(2))
  QIDDM-full    : the proposed full method (alias for run_qiddm)

These variants are constructed by patching kwargs on run_qiddm.
"""

from __future__ import annotations
import numpy as np
from algorithms.qiddm import run_qiddm
from benchmarks.problem import MCSSPInstance


def run_qiddm_no_dynamic(inst: MCSSPInstance, **kw) -> dict:
    # Setting decay=0 and theta_min=theta_max removes the schedule
    theta = 0.05 * np.pi
    r = run_qiddm(inst, theta_max=theta, theta_min=theta, decay=0.0, **kw)
    r["method"] = "QIDDM-noDyn"
    return r


def run_qiddm_no_interference(inst: MCSSPInstance, **kw) -> dict:
    r = run_qiddm(inst, eta_interference=0.0, **kw)
    r["method"] = "QIDDM-noInt"
    return r


def run_qiddm_no_local_search(inst: MCSSPInstance, **kw) -> dict:
    # local_every larger than total generations effectively disables LS
    gens = kw.get("generations", 120)
    r = run_qiddm(inst, local_every=gens + 1, **kw)
    r["method"] = "QIDDM-noLS"
    return r


def run_qiddm_no_warmstart(inst: MCSSPInstance, **kw) -> dict:
    r = run_qiddm(inst, warm_start=False, **kw)
    r["method"] = "QIDDM-noWarm"
    return r

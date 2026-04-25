"""Build a Scopus Q1 standard cover letter (.docx)."""

import os
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "paper", "Cover_Letter.docx")

doc = Document()
style = doc.styles["Normal"]
style.font.name = "Times New Roman"
style.font.size = Pt(11)


def P(text, bold=False, italic=False, align=None, size=11):
    p = doc.add_paragraph()
    if align == "right": p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    elif align == "center": p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify": p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    r = p.add_run(text)
    r.bold = bold; r.italic = italic
    r.font.name = "Times New Roman"; r.font.size = Pt(size)
    return p


# Letterhead
P("[Author Name, PhD]", bold=True, align="right")
P("[Department] · [University]", align="right")
P("[Address] · [City, Country]", align="right")
P("Email: corresponding@institution.edu", align="right")
P("ORCID: 0000-0000-0000-0000", align="right")
P("")
P("25 April 2026", align="right")
P("")

P("To the Editor-in-Chief")
P("Nexus of Research Horizon — An International Interdisciplinary Journal", italic=True)

P("")
P("Subject: Manuscript submission — \"Quantum-Inspired Dynamic Decision-Making "
  "(QIDDM): A Superposition-Based Framework for Multi-Criteria Capacitated "
  "Supplier Selection\"", bold=True, align="justify")

P("")
P("Dear Editor-in-Chief,", align="justify")
P("")
P(
    "We respectfully submit the enclosed manuscript for consideration in "
    "Nexus of Research Horizon. The work introduces Quantum-Inspired "
    "Dynamic Decision-Making (QIDDM), a hybrid metaheuristic that couples "
    "a quantum-inspired phase-rotation gate with two new components — a "
    "decision-theoretic feedback signal that adapts the rotation magnitude "
    "to landscape progress, and a multi-criteria interference vector that "
    "biases search toward criteria currently underrepresented in the global "
    "best — and applies it to a Multi-Criteria Capacitated Supplier "
    "Selection Problem (MC-CSSP) augmented with non-linear synergy, risk "
    "and diversification effects.", align="justify",
)
P("")
P("Significance and novelty:", bold=True)
P(
    "(i) QIDDM is the first quantum-inspired evolutionary algorithm, to our "
    "knowledge, to embed dynamic decision-theoretic feedback directly into "
    "the rotation gate and to modulate phase rotation by per-criterion "
    "interference; (ii) the manuscript provides a fully reproducible "
    "non-linear MC-CSSP benchmark suite that breaks the analytical "
    "optimality of greedy multi-criteria ranking and is therefore "
    "appropriate for benchmarking modern metaheuristics; (iii) we report "
    "an exact-optimality reference for small instances, an ablation study "
    "isolating each new component, a hyper-parameter sensitivity analysis, "
    "and statistical significance tests with effect sizes (Mann–Whitney U "
    "and Cliff's δ).", align="justify",
)
P("")
P("Headline results:", bold=True)
P(
    "Across five MC-CSSP instances of increasing scale (N = 20, 30, 40, 80, "
    "200) and twenty independent runs per stochastic method, QIDDM "
    "achieved the highest mean utility on every non-trivial instance, the "
    "lowest variance among stochastic methods, the fastest convergence "
    "(≥ 2× faster than GA / PSO / classical QEA), and the smallest "
    "optimality gap on the small instance for which exhaustive enumeration "
    "is feasible. Improvements are statistically significant at p < 0.001 "
    "with large Cliff's δ effect sizes.", align="justify",
)
P("")
P("Fit to scope:", bold=True)
P(
    "The manuscript bridges quantum-inspired computing, multi-criteria "
    "decision analysis, and operations research for supply networks. It "
    "speaks directly to the editorial mandate of Nexus of Research Horizon "
    "to publish interdisciplinary work that connects computational methods "
    "with practical decision-making. The supplier-selection application "
    "aligns with United Nations Sustainable Development Goal 12.5 on "
    "responsible production and SDG 9 on resilient industrial "
    "infrastructure.", align="justify",
)
P("")
P("Originality and ethics:", bold=True)
P(
    "The manuscript is original work, has not been published previously and "
    "is not under consideration elsewhere. All authors have approved the "
    "submission. The work involves no human subjects, animal experiments "
    "or sensitive data; ethical approval is therefore not applicable. The "
    "authors declare no competing financial or non-financial interests. "
    "All code and data required to reproduce every experiment, table and "
    "figure are released under an open-source license at the public "
    "repository linked in the manuscript.", align="justify",
)
P("")
P("Suggested reviewers (independent of any author institution):", bold=True)
P(
    "(1) Prof. Kuk-Hyun Han, KAIST, Republic of Korea — author of the "
    "canonical QEA framework; (2) Prof. Kannan Govindan, University of "
    "Southern Denmark — multi-criteria sustainable supplier selection; "
    "(3) Prof. Gexiang Zhang, Southwest Jiaotong University, China — "
    "quantum-inspired evolutionary algorithms.", align="justify",
)
P("")
P(
    "We thank you for your consideration and look forward to the editorial "
    "and reviewer feedback.", align="justify",
)
P("")
P("Sincerely,", align="justify")
P("")
P("[Author Name]", bold=True)
P("On behalf of all co-authors", italic=True)

doc.save(OUT)
print("Saved:", OUT)

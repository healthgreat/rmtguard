#!/usr/bin/env python
"""Build the matched-baseline execution design for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Define the next manuscript-grade head-to-head baseline experiment on
the same split framework used by the real-data ablation pilot.
Data source: Current RMTGuard benchmark control plane and SuperGrok P0/P1
feedback items.
Method notes: This script writes an execution design only. It does not claim
that Seurat, JackStraw, or permutation-PCA baselines have already been run.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_TSV = ROOT / "results" / "submission" / "matched_baseline_design.tsv"
OUT_MD = ROOT / "docs" / "matched_baseline_design.md"

DATASETS = [
    {
        "dataset_id": "kang_ifnb_pbmc",
        "dataset_label": "Kang IFN-beta PBMC",
        "role": "immune perturbation / batch-aware check",
        "label_key": "cell_type",
        "batch_key": "condition",
    },
    {
        "dataset_id": "baron_pancreas",
        "dataset_label": "Baron pancreas",
        "role": "tissue heterogeneity check",
        "label_key": "cell_type",
        "batch_key": "sample",
    },
    {
        "dataset_id": "pbmc68k_zheng2017",
        "dataset_label": "PBMC68k/Zheng 2017",
        "role": "diagnostic no-call stress context",
        "label_key": "cell_type",
        "batch_key": "none",
    },
    {
        "dataset_id": "pdac_gse263733",
        "dataset_label": "PDAC GSE263733",
        "role": "external PDAC/TME validation context",
        "label_key": "cell_type",
        "batch_key": "sample",
    },
]

METHODS = [
    {
        "method_id": "rmtguard_default_v3_3",
        "method_label": "RMTGuard default v3.3",
        "family": "RMTGuard",
        "implementation": "Python package",
        "status": "pilot_available",
        "reason": "reference method under current manuscript route",
    },
    {
        "method_id": "rmtguard_batch_residualized",
        "method_label": "RMTGuard batch residualized",
        "family": "RMTGuard ablation",
        "implementation": "Python package",
        "status": "pilot_available",
        "reason": "tests whether lower batch alignment is retained on matched splits",
    },
    {
        "method_id": "rmtguard_forced_min_10_pcs",
        "method_label": "RMTGuard forced min 10 PCs",
        "family": "negative control",
        "implementation": "Python package",
        "status": "pilot_available",
        "reason": "shows cost of bypassing no-call/PC guard",
    },
    {
        "method_id": "scanpy_default_like",
        "method_label": "Scanpy default-like",
        "family": "Scanpy",
        "implementation": "Python scanpy workflow",
        "status": "needs_matched_execution",
        "reason": "standard Python comparator on identical splits",
    },
    {
        "method_id": "scanpy_elbow_rule",
        "method_label": "Scanpy elbow-rule PC selection",
        "family": "Scanpy PC rule",
        "implementation": "Python scanpy workflow",
        "status": "needs_matched_execution",
        "reason": "strongest current raw-stability comparator must be tested with annotation and batch metrics",
    },
    {
        "method_id": "seurat_v5_default",
        "method_label": "Seurat v5 default",
        "family": "Seurat",
        "implementation": "R / Seurat v5",
        "status": "blocked_by_r_dependency_and_conversion",
        "reason": "reviewer-expected R comparator",
    },
    {
        "method_id": "seurat_v5_jackstraw",
        "method_label": "Seurat v5 JackStraw PC rule",
        "family": "Seurat PC rule",
        "implementation": "R / Seurat v5",
        "status": "blocked_by_runtime_and_r_dependency",
        "reason": "reviewer-requested permutation-like PCA comparator",
    },
    {
        "method_id": "parallel_analysis_pca",
        "method_label": "Permutation/parallel-analysis PCA",
        "family": "statistical PC rule",
        "implementation": "Python or R",
        "status": "needs_matched_execution",
        "reason": "direct statistical baseline for RMT PC selection",
    },
]

METRICS = [
    "label_ari",
    "label_nmi",
    "batch_ari",
    "batch_nmi",
    "no_call_rate",
    "cluster_count",
    "cluster_count_variance",
    "runtime_seconds",
    "peak_memory_mb",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def build_design() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for dataset in DATASETS:
        for method in METHODS:
            rows.append(
                {
                    "dataset_id": dataset["dataset_id"],
                    "dataset_label": dataset["dataset_label"],
                    "dataset_role": dataset["role"],
                    "label_key": dataset["label_key"],
                    "batch_key": dataset["batch_key"],
                    "split_framework": "reuse subsample80_pilot10 repeat seeds and 80% cell subsampling when possible",
                    "target_repeats": 20,
                    "stretch_repeats": 50,
                    "method_id": method["method_id"],
                    "method_label": method["method_label"],
                    "method_family": method["family"],
                    "implementation": method["implementation"],
                    "execution_status": method["status"],
                    "reason": method["reason"],
                    "primary_metrics": ";".join(METRICS),
                    "pass_gate": (
                        "No broad superiority claim unless paired CIs support it; "
                        "no major annotation loss; no increase in batch alignment; "
                        "PBMC68k no-call stays diagnostic rather than forced rescue."
                    ),
                    "blockers": (
                        "R/Seurat v5 installation; h5ad-to-Seurat conversion; "
                        "JackStraw runtime; matched split bookkeeping"
                    )
                    if method["family"].startswith("Seurat")
                    else "matched split bookkeeping and final runtime/memory capture",
                }
            )
    return pd.DataFrame(rows)


def build_doc(design: pd.DataFrame) -> str:
    lines = [
        "# Matched baseline design",
        "",
        "Generated by `python scripts/build_matched_baseline_design.py`.",
        "",
        "## Purpose",
        "",
        "This document defines the next head-to-head baseline experiment required before any 20-50 JIF submission route can be reopened.",
        "",
        "## Non-negotiable Design Rules",
        "",
        "- Use the same dataset preparation, same repeat IDs, and same 80% subsampling framework wherever possible.",
        "- Report label ARI/NMI, batch ARI/NMI, no-call rate, cluster-number variance, runtime, and memory for every method.",
        "- Treat PBMC68k/Zheng 2017 as a diagnostic no-call stress context. Do not promote forced clustering as a rescue.",
        "- Seurat v5 and JackStraw rows are currently design rows only until the R dependency, conversion, and runtime blockers are resolved.",
        "- Apply paired bootstrap or paired permutation tests after the matched outputs exist, with multiple-testing correction across datasets and metrics.",
        "",
        "## Dataset Coverage",
        "",
        "| Dataset | Role | Label key | Batch key |",
        "| --- | --- | --- | --- |",
    ]
    for dataset in DATASETS:
        lines.append(
            f"| {dataset['dataset_label']} | {dataset['role']} | `{dataset['label_key']}` | `{dataset['batch_key']}` |"
        )
    lines.extend(
        [
            "",
            "## Method Coverage",
            "",
            "| Method | Family | Status | Why included |",
            "| --- | --- | --- | --- |",
        ]
    )
    for method in METHODS:
        lines.append(
            f"| {method['method_label']} | {method['family']} | `{method['status']}` | {method['reason']} |"
        )
    lines.extend(
        [
            "",
            "## Output Contract",
            "",
            f"- Design TSV: `{_rel(OUT_TSV)}`",
            "- Final result table should be written separately after actual execution, not inferred from this design.",
            "- The 20-50 JIF route remains blocked until matched baseline results exist.",
            "",
            "## Current Row Count",
            "",
            f"- Datasets: `{design['dataset_id'].nunique()}`",
            f"- Methods: `{design['method_id'].nunique()}`",
            f"- Design rows: `{len(design)}`",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    design = build_design()
    _atomic_write_tsv(design, OUT_TSV)
    _atomic_write_text(build_doc(design), OUT_MD)
    print(_rel(OUT_TSV))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

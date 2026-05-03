#!/usr/bin/env python
"""Summarize Seurat JackStraw comparator runs.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Record whether official Seurat JackStraw can execute on the prepared
MatrixMarket benchmark inputs and whether the current run has manuscript-grade
repeat depth.
Data source: results/submission/seurat_matched_pilot/seurat_matched_baseline_detail.tsv.
Method notes: This distinguishes a feasibility audit from a 20-repeat,
20-JackStraw-replicate comparator candidate.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DETAIL = (
    ROOT
    / "results"
    / "submission"
    / "seurat_matched_baseline_detail.tsv"
)
OUT_SUMMARY = ROOT / "results" / "submission" / "seurat_jackstraw_feasibility_summary.tsv"
OUT_STATUS = ROOT / "results" / "submission" / "seurat_jackstraw_feasibility_status.tsv"
OUT_MD = ROOT / "docs" / "seurat_jackstraw_feasibility.md"
EXPECTED_DATASETS = [
    "pbmc3k_10x",
    "kang_ifnb_pbmc",
    "baron_pancreas",
    "paul15_hematopoiesis",
    "pbmc68k_zheng2017",
    "pdac_gse154778",
    "pdac_gse263733",
]


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False)
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _fmt(value: object, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "NA"
    if np.isnan(number):
        return "NA"
    return f"{number:.{digits}f}"


def _infer_jackstraw_replicates(group: pd.DataFrame) -> int:
    if "pc_rule" not in group.columns:
        return 0
    rules = group["pc_rule"].astype(str)
    values: list[int] = []
    for rule in rules:
        parts = rule.split("_")
        for idx, part in enumerate(parts):
            if idx > 0 and part == "replicates":
                try:
                    values.append(int(parts[idx - 1]))
                except ValueError:
                    pass
    return max(values) if values else 0


def build_summary(detail: pd.DataFrame, run_label: str) -> pd.DataFrame:
    subset = detail.loc[
        detail["run_label"].eq(run_label)
        & detail["method_id"].eq("seurat_v5_jackstraw")
    ].copy()
    rows: list[dict[str, object]] = []
    for dataset_id, group in subset.groupby("dataset_id"):
        repeats = int(group["repeat"].nunique())
        jackstraw_replicates = _infer_jackstraw_replicates(group)
        evidence_level = (
            "manuscript_candidate"
            if repeats >= 20 and jackstraw_replicates >= 20
            else "pilot10_pass"
            if repeats >= 10
            else "feasibility_only"
        )
        rows.append(
            {
                "run_label": run_label,
                "dataset_id": dataset_id,
                "method_id": "seurat_v5_jackstraw",
                "n_repeats": repeats,
                "jackstraw_replicates": jackstraw_replicates,
                "mean_selected_pcs": float(pd.to_numeric(group["selected_pcs"]).mean()),
                "mean_cluster_n": float(pd.to_numeric(group["cluster_n"]).mean()),
                "mean_runtime_seconds": float(
                    pd.to_numeric(group["runtime_seconds"], errors="coerce").mean()
                ),
                "mean_label_ari": float(
                    pd.to_numeric(group["label_ari"], errors="coerce").mean()
                ),
                "mean_batch_ari": float(
                    pd.to_numeric(group["batch_ari"], errors="coerce").mean()
                ),
                "execution_status": ";".join(sorted(group["execution_status"].unique())),
                "analysis_status": ";".join(sorted(group["analysis_status"].unique())),
                "evidence_level": evidence_level,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "run_label",
                "dataset_id",
                "method_id",
                "n_repeats",
                "jackstraw_replicates",
                "mean_selected_pcs",
                "mean_cluster_n",
                "mean_runtime_seconds",
                "mean_label_ari",
                "mean_batch_ari",
                "execution_status",
                "analysis_status",
                "evidence_level",
            ]
        )
    return pd.DataFrame(rows).sort_values("dataset_id")


def build_status(summary: pd.DataFrame, run_label: str) -> pd.DataFrame:
    datasets = set(summary["dataset_id"].astype(str)) if not summary.empty else set()
    min_repeats = int(summary["n_repeats"].min()) if not summary.empty else 0
    min_jackstraw_replicates = (
        int(pd.to_numeric(summary["jackstraw_replicates"], errors="coerce").min())
        if not summary.empty
        else 0
    )
    runtime_max = (
        float(summary["mean_runtime_seconds"].max()) if not summary.empty else np.nan
    )
    feasibility_pass = set(EXPECTED_DATASETS).issubset(datasets) and min_repeats >= 1
    manuscript_candidate = (
        set(EXPECTED_DATASETS).issubset(datasets)
        and min_repeats >= 20
        and min_jackstraw_replicates >= 20
    )
    rows = [
        {
            "check_id": "seurat_jackstraw_feasibility",
            "status": "manuscript_candidate"
            if manuscript_candidate
            else "feasibility_pass"
            if feasibility_pass
            else "incomplete",
            "scope": f"{len(datasets)}_of_{len(EXPECTED_DATASETS)}_datasets_min_repeats_{min_repeats}_min_jackstraw_replicates_{min_jackstraw_replicates}",
            "run_label": run_label,
            "evidence": _rel(OUT_SUMMARY),
            "interpretation": "Official Seurat JackStraw has 20-repeat, 20-replicate comparator-candidate evidence on the prepared MatrixMarket bridge."
            if manuscript_candidate
            else "Official Seurat JackStraw can execute on the prepared MatrixMarket bridge."
            if feasibility_pass
            else "Official Seurat JackStraw feasibility is not complete across the prepared datasets.",
            "remaining_work": "Freeze the paired comparator table and expand to additional datasets."
            if manuscript_candidate
            else "Scale to a proper comparator run with more JackStraw replicates and 10-20+ subsampling repeats, or document an explicit runtime-based omission.",
            "max_mean_runtime_seconds": runtime_max,
        },
        {
            "check_id": "manuscript_grade_jackstraw",
            "status": "manuscript_candidate" if manuscript_candidate else "not_ready",
            "scope": "publication_gate",
            "run_label": run_label,
            "evidence": _rel(OUT_SUMMARY),
            "interpretation": "JackStraw repeat depth is sufficient for a comparator-candidate table."
            if manuscript_candidate
            else "Feasibility does not equal a manuscript-grade JackStraw comparator.",
            "remaining_work": "Use only after paired RMTGuard-vs-Seurat statistics are regenerated and frozen."
            if manuscript_candidate
            else "Run final repeats and paired tests before using JackStraw as a full head-to-head baseline.",
            "max_mean_runtime_seconds": runtime_max,
        },
    ]
    return pd.DataFrame(rows)


def build_markdown(summary: pd.DataFrame, status: pd.DataFrame, run_label: str) -> str:
    lines = [
        "# Seurat JackStraw Feasibility Report",
        "",
        "Generated by `python scripts/build_seurat_jackstraw_feasibility_report.py`.",
        "",
        "## Bottom Line",
        "",
        "- Official Seurat JackStraw was tested on the same MatrixMarket bridge used for the matched Seurat baselines.",
        "- The status table distinguishes `feasibility_only` from `manuscript_candidate` repeat depth.",
        "- A `manuscript_candidate` status means at least 20 subsampling repeats and at least 20 JackStraw replicates across all prepared datasets.",
        "",
        "## Status",
        "",
        "| Check | Status | Scope | Remaining work |",
        "| --- | --- | --- | --- |",
    ]
    for row in status.to_dict("records"):
        lines.append(
            f"| {row['check_id']} | {row['status']} | {row['scope']} | {row['remaining_work']} |"
        )
    lines.extend(
        [
            "",
            "## Dataset Summary",
            "",
            "| Dataset | Repeats | JackStraw replicates | Selected PCs | Clusters | Runtime seconds | Label ARI | Batch ARI |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['dataset_id']} | {row['n_repeats']} | {row['jackstraw_replicates']} | "
            f"{_fmt(row['mean_selected_pcs'], 1)} | {_fmt(row['mean_cluster_n'], 1)} | "
            f"{_fmt(row['mean_runtime_seconds'], 2)} | "
            f"{_fmt(row['mean_label_ari'])} | {_fmt(row['mean_batch_ari'])} |"
        )
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            f"- Detail TSV: `{_rel(DETAIL)}`",
            f"- Summary TSV: `{_rel(OUT_SUMMARY)}`",
            f"- Status TSV: `{_rel(OUT_STATUS)}`",
            f"- Run label: `{run_label}`",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Seurat JackStraw feasibility.")
    parser.add_argument("--detail", type=Path, default=DETAIL)
    parser.add_argument("--run-label", default="seurat_jackstraw_subsample80_20x20_mtx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.detail.exists():
        raise FileNotFoundError(f"Missing Seurat baseline detail TSV: {_rel(args.detail)}")
    detail = pd.read_csv(args.detail, sep="\t")
    summary = build_summary(detail, args.run_label)
    status = build_status(summary, args.run_label)
    _atomic_write_tsv(summary, OUT_SUMMARY)
    _atomic_write_tsv(status, OUT_STATUS)
    _atomic_write_text(OUT_MD, build_markdown(summary, status, args.run_label))
    print(_rel(OUT_SUMMARY))
    print(_rel(OUT_STATUS))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

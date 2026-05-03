#!/usr/bin/env python
"""Summarize official Seurat matched-baseline smoke runs.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Convert official Seurat v5 matched baseline output into a concise
status report for the RMTGuard publication-readiness audit.
Data source: results/submission/seurat_matched_pilot/*.tsv and
data/processed/seurat_mtx/seurat_mtx_manifest.tsv.
Method notes: This report distinguishes smoke-test executability from
manuscript-grade 10-50 repeat evidence.
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
MANIFEST = ROOT / "data" / "processed" / "seurat_mtx" / "seurat_mtx_manifest.tsv"
OUT_SUMMARY = ROOT / "results" / "submission" / "seurat_matched_baseline_summary.tsv"
OUT_STATUS = ROOT / "results" / "submission" / "seurat_matched_baseline_status.tsv"
OUT_MD = ROOT / "docs" / "seurat_matched_baseline.md"
EXPECTED_DATASETS = [
    "pbmc3k_10x",
    "kang_ifnb_pbmc",
    "baron_pancreas",
    "paul15_hematopoiesis",
    "pbmc68k_zheng2017",
    "pdac_gse154778",
    "pdac_gse263733",
]
FINAL_METHODS = [
    "seurat_v5_fixed_30",
    "seurat_v5_fixed_50",
    "seurat_v5_elbow",
    "seurat_v5_jackstraw",
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


def _mean_ci(values: pd.Series) -> tuple[float, float, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return np.nan, np.nan, np.nan
    mean = float(numeric.mean())
    if len(numeric) < 2:
        return mean, np.nan, np.nan
    se = float(numeric.std(ddof=1) / np.sqrt(len(numeric)))
    return mean, mean - 1.96 * se, mean + 1.96 * se


def _build_summary(detail: pd.DataFrame, run_label: str) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    subset = detail.loc[detail["run_label"].eq(run_label)].copy()
    for (dataset_id, method_id), group in subset.groupby(["dataset_id", "method_id"]):
        label_mean, label_low, label_high = _mean_ci(group["label_ari"])
        batch_mean, batch_low, batch_high = _mean_ci(group["batch_ari"])
        rows.append(
            {
                "run_label": run_label,
                "dataset_id": dataset_id,
                "method_id": method_id,
                "n_repeats": int(group["repeat"].nunique()),
                "n_rows": int(len(group)),
                "mean_label_ari": label_mean,
                "label_ari_ci95_low": label_low,
                "label_ari_ci95_high": label_high,
                "mean_batch_ari": batch_mean,
                "batch_ari_ci95_low": batch_low,
                "batch_ari_ci95_high": batch_high,
                "mean_cluster_n": float(pd.to_numeric(group["cluster_n"]).mean()),
                "mean_selected_pcs": float(pd.to_numeric(group["selected_pcs"]).mean()),
                "mean_runtime_seconds": float(
                    pd.to_numeric(group["runtime_seconds"], errors="coerce").mean()
                ),
                "execution_status": ";".join(sorted(group["execution_status"].unique())),
                "analysis_status": ";".join(sorted(group["analysis_status"].unique())),
                "evidence_level": "manuscript_candidate"
                if group["repeat"].nunique() >= 20
                else "pilot10_pass"
                if group["repeat"].nunique() >= 10
                else "smoke_only",
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset_id", "method_id"])


def _build_status(
    detail: pd.DataFrame, manifest: pd.DataFrame, run_label: str
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    manifest_datasets = set(manifest.get("dataset_id", pd.Series(dtype=str)).astype(str))
    smoke = detail.loc[detail["run_label"].eq(run_label)].copy()
    smoke_datasets = set(smoke.get("dataset_id", pd.Series(dtype=str)).astype(str))
    rows.append(
        {
            "check_id": "seurat_mtx_bridge",
            "status": "pass" if set(EXPECTED_DATASETS).issubset(manifest_datasets) else "fail",
            "scope": f"{len(manifest_datasets & set(EXPECTED_DATASETS))}_of_{len(EXPECTED_DATASETS)}_prepared_datasets",
            "evidence": _rel(MANIFEST),
            "interpretation": "MatrixMarket bridge exists for expected datasets and avoids direct h5ad sparse import failure modes.",
            "remaining_work": "Keep large MatrixMarket files out of Git; document regeneration script in the public repository.",
        }
    )
    for method in FINAL_METHODS:
        method_rows = smoke.loc[smoke["method_id"].eq(method)]
        datasets = set(method_rows["dataset_id"].astype(str))
        repeat_depths = (
            method_rows.groupby("dataset_id")["repeat"].nunique().to_dict()
            if not method_rows.empty
            else {}
        )
        min_repeats = min(repeat_depths.values()) if repeat_depths else 0
        if set(EXPECTED_DATASETS).issubset(datasets) and min_repeats >= 20:
            status = "manuscript_candidate"
        elif set(EXPECTED_DATASETS).issubset(datasets) and min_repeats >= 10:
            status = "pilot10_pass"
        elif set(EXPECTED_DATASETS).issubset(datasets):
            status = "smoke_pass"
        elif datasets:
            status = "incomplete"
        else:
            status = "not_run_in_current_run_label"
        rows.append(
            {
                "check_id": method,
                "status": status,
                "scope": f"{len(datasets)}_of_{len(EXPECTED_DATASETS)}_datasets_min_repeats_{min_repeats}",
                "evidence": _rel(DETAIL),
                "interpretation": "Official Seurat v5 matched baseline is executable on the shared 80% subsampling framework.",
                "remaining_work": "Add paired statistics against RMTGuard and final comparator freeze before manuscript use."
                if status == "manuscript_candidate"
                else "Scale to 20+ repeats with paired statistics before manuscript use."
                if status == "pilot10_pass"
                else "Run on the same split framework; JackStraw may require a dedicated runtime budget or documented omission."
                if status == "not_run_in_current_run_label"
                else "Scale to 10-20+ repeats with confidence intervals before manuscript use.",
            }
        )
    core_pilot10 = all(
        row["status"] in {"pilot10_pass", "manuscript_candidate"}
        for row in rows
        if row["check_id"]
        in {"seurat_v5_fixed_30", "seurat_v5_fixed_50", "seurat_v5_elbow"}
    )
    jackstraw_ready = any(
        row["check_id"] == "seurat_v5_jackstraw"
        and row["status"] in {"pilot10_pass", "manuscript_candidate"}
        for row in rows
    )
    core_20 = all(
        row["status"] == "manuscript_candidate"
        for row in rows
        if row["check_id"]
        in {"seurat_v5_fixed_30", "seurat_v5_fixed_50", "seurat_v5_elbow"}
    )
    full_20 = all(
        row["status"] == "manuscript_candidate"
        for row in rows
        if row["check_id"] in set(FINAL_METHODS)
    )
    rows.append(
        {
            "check_id": "manuscript_grade_status",
            "status": "complete_20_repeat_candidate"
            if full_20
            else "fixed_pc_elbow_20_repeat_jackstraw_missing"
            if core_20 and not jackstraw_ready
            else "pilot10_partial_not_ready"
            if core_pilot10 and not jackstraw_ready
            else "not_ready",
            "scope": "publication_gate",
            "evidence": f"{_rel(OUT_SUMMARY)};{_rel(OUT_STATUS)}",
            "interpretation": "Official Seurat fixed-PC, elbow, and JackStraw comparators have 20-repeat candidate evidence."
            if full_20
            else "This closes the core official Seurat fixed-PC/elbow pilot blocker, not the full statistical-evidence blocker.",
            "remaining_work": "Add paired statistics against RMTGuard, freeze the comparator table, and expand to additional datasets."
            if full_20
            else "Run final JackStraw repeats where feasible, add paired statistics against RMTGuard, and freeze the comparator table.",
        }
    )
    return pd.DataFrame(rows)


def _build_markdown(summary: pd.DataFrame, status: pd.DataFrame, run_label: str) -> str:
    def fmt(value: object) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "NA"
        if np.isnan(numeric):
            return "NA"
        return f"{numeric:.3f}"

    lines = [
        "# Official Seurat Matched-Baseline Report",
        "",
        "Generated by `python scripts/build_seurat_matched_baseline_report.py`.",
        "",
        "## Bottom Line",
        "",
        "- `MatrixMarket` bridge: generated for PBMC3k, Kang IFN-beta PBMC, Baron pancreas, Paul15 hematopoiesis, PBMC68k/Zheng 2017, PDAC GSE154778, and PDAC GSE263733.",
        "- Official Seurat v5 core baselines: fixed 30 PCs, fixed 50 PCs, elbow-rule PCs, and JackStraw PCs are tracked on the shared 80% subsampling seed logic when present in the selected run label.",
        "- Evidence level: `manuscript_candidate` means at least 20 repeats across all four prepared datasets for that method. This still needs paired statistics and final comparator freeze.",
        "- Claim boundary: this supports baseline executability only. It does not support a stability or annotation-superiority claim.",
        "",
        "## Status Checks",
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
            "## Baseline Summary",
            "",
            "| Dataset | Method | Repeats | Mean label ARI | Mean batch ARI | Mean clusters | Mean selected PCs |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary.to_dict("records"):
        lines.append(
            f"| {row['dataset_id']} | {row['method_id']} | {row['n_repeats']} | "
            f"{fmt(row['mean_label_ari'])} | {fmt(row['mean_batch_ari'])} | "
            f"{float(row['mean_cluster_n']):.1f} | {float(row['mean_selected_pcs']):.1f} |"
        )
    lines.extend(
        [
            "",
            "## Source Artifacts",
            "",
            f"- Detail TSV: `{_rel(DETAIL)}`",
            f"- Summary TSV: `{_rel(OUT_SUMMARY)}`",
            f"- Status TSV: `{_rel(OUT_STATUS)}`",
            f"- MatrixMarket manifest: `{_rel(MANIFEST)}`",
            f"- Run label: `{run_label}`",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize official Seurat matched-baseline smoke runs."
    )
    parser.add_argument("--detail", type=Path, default=DETAIL)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--run-label", default="seurat_jackstraw_subsample80_20x20_mtx")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.detail.exists():
        raise FileNotFoundError(f"Missing Seurat matched detail TSV: {_rel(args.detail)}")
    if not args.manifest.exists():
        raise FileNotFoundError(f"Missing Seurat MatrixMarket manifest: {_rel(args.manifest)}")
    detail = pd.read_csv(args.detail, sep="\t")
    manifest = pd.read_csv(args.manifest, sep="\t")
    summary = _build_summary(detail, args.run_label)
    status = _build_status(detail, manifest, args.run_label)
    _atomic_write_tsv(summary, OUT_SUMMARY)
    _atomic_write_tsv(status, OUT_STATUS)
    _atomic_write_text(OUT_MD, _build_markdown(summary, status, args.run_label))
    print(_rel(OUT_SUMMARY))
    print(_rel(OUT_STATUS))
    print(_rel(OUT_MD))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

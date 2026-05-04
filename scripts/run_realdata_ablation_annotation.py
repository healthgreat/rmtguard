#!/usr/bin/env python
"""Run real-data annotation checks for RMTGuard component ablations.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Add public real-data annotation recovery and batch-alignment checks
to the component-ablation control plane.
Data source: Prepared public h5ad files in data/processed/.
Method notes: Uses anndata.read_h5ad directly to avoid importing scanpy on the
hot path. Defaults are draft-scale and resumable; final manuscript use requires
20-50 repeats and matched external baselines.
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from rmtguard import RMTGuard, RMTGuardConfig

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT_DIR = ROOT / "results" / "ablation"
DETAIL = OUT_DIR / "realdata_ablation_annotation_detail.tsv"
SUMMARY = OUT_DIR / "realdata_ablation_annotation_summary.tsv"
DOC = ROOT / "docs" / "realdata_ablation_annotation.md"

DATASETS = {
    "paul15_hematopoiesis": {
        "filename": "paul15_hematopoiesis.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
    },
    "kang_ifnb_pbmc": {
        "filename": "kang_ifnb_pbmc.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
    },
    "baron_pancreas": {
        "filename": "baron_pancreas.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
    },
    "pbmc68k_zheng2017": {
        "filename": "pbmc68k_zheng2017.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
    },
    "pdac_gse263733": {
        "filename": "pdac_gse263733.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
    },
}


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


def _read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, sep="\t")
    if "run_label" not in df.columns:
        df["run_label"] = "default"
    if "subsample_fraction" not in df.columns:
        df["subsample_fraction"] = 1.0
    if "source_n_cells" not in df.columns and "n_cells" in df.columns:
        df["source_n_cells"] = df["n_cells"]
    if "subsample_n_cells" not in df.columns and "n_cells" in df.columns:
        df["subsample_n_cells"] = df["n_cells"]
    return df


def _safe_metric(labels_true, labels_pred, metric) -> float:
    labels_true = np.asarray(labels_true).astype(str)
    labels_pred = np.asarray(labels_pred).astype(str)
    if labels_true.size == 0 or np.unique(labels_true).size < 2:
        return math.nan
    return float(metric(labels_true, labels_pred))


def _matrix(adata: ad.AnnData):
    return adata.layers["counts"] if "counts" in adata.layers else adata.X


def _base_config(args: argparse.Namespace) -> RMTGuardConfig:
    return RMTGuardConfig(
        hvg_grid=tuple(args.hvg_grid),
        max_pcs=args.max_pcs,
        whiten="biwhiten",
        pc_rule="mp_tw",
        hvg_rule="spectral_stability",
        hvg_score="normalized_dispersion",
        embedding_rule="adaptive_near_edge",
        embedding_source="standard_pca",
        near_edge_window=1.25,
        embedding_stability_repeats=args.embedding_stability_repeats,
        embedding_stability_threshold=0.75,
        embedding_subsample_fraction=0.80,
        resolution_rule="graph_modularity",
        graph_resolution_grid=(1.0,),
        rare_state_guard="adaptive_binary_split",
        rare_state_min_fraction=0.015,
        rare_state_max_fraction=0.15,
        rare_state_min_cells=4,
        rare_state_min_separation=3.0,
        rare_state_min_silhouette=0.35,
        n_permutations=0,
        tw_alpha=0.01,
        random_state=args.random_state,
        cluster_grid=tuple(range(2, args.max_clusters + 1)),
    )


def _variants(args: argparse.Namespace) -> list[dict[str, Any]]:
    base = _base_config(args)
    variants = [
        {
            "ablation_id": "default_v3_3",
            "component_family": "reference",
            "variant_label": "default RMTGuard v3.3",
            "config": base,
        },
        {
            "ablation_id": "embedding_strict_signal",
            "component_family": "adaptive_embedding",
            "variant_label": "strict signal embedding",
            "config": replace(base, embedding_rule="strict_signal"),
        },
        {
            "ablation_id": "hvg_rule_dispersion",
            "component_family": "hvg_selection",
            "variant_label": "dispersion HVG",
            "config": replace(base, hvg_rule="dispersion"),
        },
        {
            "ablation_id": "rare_state_guard_off",
            "component_family": "rare_state_guard",
            "variant_label": "rare-state guard off",
            "config": replace(base, rare_state_guard="off"),
        },
        {
            "ablation_id": "force_min_embedding_pcs_10",
            "component_family": "no_call_contract",
            "variant_label": "force minimum 10 embedding PCs",
            "config": replace(base, min_embedding_pcs=10),
        },
        {
            "ablation_id": "whiten_zscore",
            "component_family": "biwhitening",
            "variant_label": "z-score whitening",
            "config": replace(base, whiten="zscore"),
        },
        {
            "ablation_id": "batch_residualized",
            "component_family": "batch_residualization",
            "variant_label": "batch residualized fit",
            "config": base,
            "use_batches": True,
        },
    ]
    if args.ablation_ids:
        wanted = set(args.ablation_ids)
        variants = [variant for variant in variants if variant["ablation_id"] in wanted]
        missing = wanted - {variant["ablation_id"] for variant in variants}
        if missing:
            raise ValueError(f"Unknown ablation id(s): {', '.join(sorted(missing))}")
    return variants


def _key(row: dict[str, Any]) -> tuple[str, str, str, int, str]:
    return (
        str(row["dataset_id"]),
        str(row["ablation_id"]),
        str(row["component_family"]),
        int(row["repeat"]),
        str(row.get("run_label", "default")),
    )


def _append(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    rows.append(row)
    _atomic_write_tsv(pd.DataFrame(rows), DETAIL)


def run_detail(args: argparse.Namespace) -> pd.DataFrame:
    existing = pd.DataFrame() if args.force else _read_existing(DETAIL)
    rows: list[dict[str, Any]] = existing.to_dict(orient="records") if not existing.empty else []
    completed = {_key(row) for row in rows} if rows else set()
    variants = _variants(args)

    for dataset_id in args.datasets:
        spec = DATASETS[dataset_id]
        path = args.processed_dir / spec["filename"]
        if not path.exists():
            raise FileNotFoundError(f"Prepared dataset missing: {path}")
        adata = ad.read_h5ad(path)
        matrix_all = _matrix(adata)
        labels_all = adata.obs[spec["label_key"]].to_numpy()
        batches_all = (
            adata.obs[spec["batch_key"]].to_numpy()
            if spec["batch_key"] in adata.obs
            else None
        )
        source_n_cells = int(adata.n_obs)
        dataset_seed = sum(ord(ch) for ch in dataset_id)
        if not 0 < args.subsample_fraction <= 1:
            raise ValueError("--subsample-fraction must be in (0, 1].")
        for repeat in range(args.n_repeats):
            if args.subsample_fraction < 1.0:
                rng = np.random.default_rng(
                    args.random_state + repeat * 997 + dataset_seed
                )
                subsample_n = max(
                    2, int(round(source_n_cells * args.subsample_fraction))
                )
                idx = np.sort(rng.choice(source_n_cells, subsample_n, replace=False))
            else:
                idx = np.arange(source_n_cells)
            matrix = matrix_all[idx, :]
            labels = labels_all[idx]
            batches = batches_all[idx] if batches_all is not None else None
            for variant in variants:
                plan = {
                    "run_label": args.run_label,
                    "dataset_id": dataset_id,
                    "ablation_id": variant["ablation_id"],
                    "component_family": variant["component_family"],
                    "repeat": repeat,
                }
                if _key(plan) in completed:
                    continue
                seed = (
                    args.random_state
                    + repeat * 101
                    + dataset_seed
                    + sum(ord(ch) for ch in variant["ablation_id"])
                )
                fit_batches = batches if variant.get("use_batches") else None
                result = RMTGuard(replace(variant["config"], random_state=seed)).fit(
                    matrix,
                    batches=fit_batches,
                    benchmark_metadata={
                        "dataset_id": dataset_id,
                        "label_key": spec["label_key"],
                        "batch_key": spec["batch_key"],
                        "ablation_id": variant["ablation_id"],
                    },
                )
                row = {
                    **plan,
                    "variant_label": variant["variant_label"],
                    "n_cells": int(len(labels)),
                    "source_n_cells": source_n_cells,
                    "subsample_n_cells": int(len(labels)),
                    "subsample_fraction": float(args.subsample_fraction),
                    "n_genes": int(adata.n_vars),
                    "label_key": spec["label_key"],
                    "batch_key": spec["batch_key"],
                    "label_n": int(pd.Series(labels).nunique()),
                    "batch_n": int(pd.Series(batches).nunique()) if batches is not None else 0,
                    "analysis_status": result.analysis_status,
                    "no_call_reason": result.no_call_reason,
                    "n_signal_pcs": int(result.n_signal_pcs),
                    "n_embedding_pcs": int(result.n_embedding_pcs),
                    "accepted_embedding_pcs": int(
                        result.embedding_diagnostics.get(
                            "accepted_embedding_pcs", result.n_embedding_pcs
                        )
                    ),
                    "cluster_n": int(result.cluster_n) if result.cluster_n is not None else 0,
                    "selected_hvg_n": int(result.selected_hvg_n),
                    "runtime_seconds": result.benchmark_metadata["runtime_seconds"],
                    "peak_memory_mb": result.benchmark_metadata["peak_memory_mb"],
                    "label_ari": _safe_metric(labels, result.cluster_labels, adjusted_rand_score),
                    "label_nmi": _safe_metric(labels, result.cluster_labels, normalized_mutual_info_score),
                    "batch_ari": (
                        _safe_metric(batches, result.cluster_labels, adjusted_rand_score)
                        if batches is not None
                        else math.nan
                    ),
                    "batch_nmi": (
                        _safe_metric(batches, result.cluster_labels, normalized_mutual_info_score)
                        if batches is not None
                        else math.nan
                    ),
                    "config_whiten": variant["config"].whiten,
                    "config_hvg_rule": variant["config"].hvg_rule,
                    "config_embedding_rule": variant["config"].embedding_rule,
                    "config_rare_state_guard": variant["config"].rare_state_guard,
                    "config_min_embedding_pcs": variant["config"].min_embedding_pcs,
                    "batch_aware_fit": bool(variant.get("use_batches", False)),
                }
                _append(rows, row)
                completed.add(_key(row))
        adata.file.close() if getattr(adata, "isbacked", False) else None
    return pd.DataFrame(rows)


def _ci95(values: pd.Series) -> tuple[float, float, float]:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    if vals.empty:
        return math.nan, math.nan, math.nan
    mean = float(vals.mean())
    if len(vals) == 1:
        return mean, mean, math.nan
    sem = float(vals.std(ddof=1) / math.sqrt(len(vals)))
    margin = 1.96 * sem
    return mean - margin, mean + margin, float(vals.std(ddof=1))


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    if detail.empty:
        return pd.DataFrame()
    if "run_label" not in detail.columns:
        detail["run_label"] = "default"
    if "subsample_fraction" not in detail.columns:
        detail["subsample_fraction"] = 1.0
    rows = []
    for keys, group in detail.groupby(
        [
            "run_label",
            "subsample_fraction",
            "dataset_id",
            "component_family",
            "ablation_id",
            "variant_label",
        ],
        dropna=False,
    ):
        (
            run_label,
            subsample_fraction,
            dataset_id,
            component_family,
            ablation_id,
            variant_label,
        ) = keys
        label_ci_low, label_ci_high, label_sd = _ci95(group["label_ari"])
        batch_ci_low, batch_ci_high, batch_sd = _ci95(group["batch_ari"])
        rows.append(
            {
                "run_label": run_label,
                "subsample_fraction": float(subsample_fraction),
                "dataset_id": dataset_id,
                "component_family": component_family,
                "ablation_id": ablation_id,
                "variant_label": variant_label,
                "n_rows": int(len(group)),
                "n_repeats": int(group["repeat"].nunique()),
                "mean_label_ari": float(group["label_ari"].mean()),
                "label_ari_ci95_low": label_ci_low,
                "label_ari_ci95_high": label_ci_high,
                "label_ari_sd": label_sd,
                "mean_label_nmi": float(group["label_nmi"].mean()),
                "mean_batch_ari": float(group["batch_ari"].mean()),
                "batch_ari_ci95_low": batch_ci_low,
                "batch_ari_ci95_high": batch_ci_high,
                "batch_ari_sd": batch_sd,
                "mean_batch_nmi": float(group["batch_nmi"].mean()),
                "mean_signal_pcs": float(group["n_signal_pcs"].mean()),
                "mean_embedding_pcs": float(group["n_embedding_pcs"].mean()),
                "mean_cluster_n": float(group["cluster_n"].mean()),
                "no_call_rate": float(
                    (group["analysis_status"] == "diagnostic_no_call").mean()
                ),
                "mean_runtime_seconds": float(group["runtime_seconds"].mean()),
            }
        )
    return pd.DataFrame(rows).sort_values(
        ["run_label", "dataset_id", "component_family", "ablation_id"]
    )


def build_doc(summary: pd.DataFrame, args: argparse.Namespace) -> str:
    if summary.empty:
        status = "No real-data ablation annotation rows are available."
        accumulated_datasets = []
        accumulated_run_labels = []
    else:
        accumulated_datasets = sorted(summary["dataset_id"].astype(str).unique())
        accumulated_run_labels = sorted(summary["run_label"].astype(str).unique())
        default = summary[summary["ablation_id"] == "default_v3_3"]
        forced = summary[summary["ablation_id"] == "force_min_embedding_pcs_10"]
        max_repeat_depth = int(summary["n_repeats"].max())
        status = (
            f"Accumulated run contains {int(summary['n_rows'].sum())} detail rows across "
            f"{summary['dataset_id'].nunique()} dataset(s). Default mean label ARI is "
            f"{default['mean_label_ari'].mean():.3f}; forced-min-PC mean label ARI is "
            f"{forced['mean_label_ari'].mean():.3f}. Maximum repeated-split depth is "
            f"{max_repeat_depth} repeat(s)."
        )
    status_line = (
        "- Status: manuscript-grade 20-repeat real-data annotation depth reached for the requested component-ablation set; final journal use still requires claim-boundary review and matched source-data freeze."
        if not summary.empty and max_repeat_depth >= 20
        else "- Status: repeated-split pilot when repeat depth is 10; final manuscript use still requires 20-50 repeats plus matched baselines."
    )
    lines = [
        "# Real-data component-ablation annotation checks",
        "",
        "Generated by `python scripts/run_realdata_ablation_annotation.py`.",
        "",
        "## Scope",
        "",
        f"- Requested datasets for this invocation: {', '.join(args.datasets)}",
        f"- Datasets currently present in accumulated summary: {', '.join(accumulated_datasets) if accumulated_datasets else 'none'}",
        f"- Run labels currently present: {', '.join(accumulated_run_labels) if accumulated_run_labels else 'none'}",
        f"- Requested repeats per dataset/variant for this invocation: {args.n_repeats}",
        f"- Run label for this invocation: `{args.run_label}`",
        f"- Subsample fraction for this invocation: `{args.subsample_fraction}`",
        "- Metrics: ARI/NMI versus cell-type annotation and ARI/NMI versus batch labels.",
        status_line,
        "",
        "## Bottom Line",
        "",
        f"- {status}",
        "",
        "## Summary Table",
        "",
        "| Run | Dataset | Component | Variant | Rows | Repeats | Subsample | Label ARI | Label ARI 95% CI | Batch ARI | Batch ARI 95% CI | Signal PCs | Cluster n | No-call |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in summary.itertuples(index=False):
        lines.append(
            f"| {row.run_label} | {row.dataset_id} | {row.component_family} | {row.variant_label} | {int(row.n_rows)} | {int(row.n_repeats)} | {row.subsample_fraction:.2f} | {row.mean_label_ari:.3f} | {row.label_ari_ci95_low:.3f}-{row.label_ari_ci95_high:.3f} | {row.mean_batch_ari:.3f} | {row.batch_ari_ci95_low:.3f}-{row.batch_ari_ci95_high:.3f} | {row.mean_signal_pcs:.2f} | {row.mean_cluster_n:.2f} | {row.no_call_rate:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            "- Direct evidence: public prepared h5ad files and their existing annotation columns.",
            "- Current limitation: this is an annotation-recovery check on prepared public datasets; it does not by itself prove broad stability superiority.",
            "- Interpretation: low batch ARI is desirable only when label ARI remains acceptable.",
            "",
            "## Output Files",
            "",
            f"- Detail table: `{_rel(DETAIL)}`",
            f"- Summary table: `{_rel(SUMMARY)}`",
            f"- Report: `{_rel(DOC)}`",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED)
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["kang_ifnb_pbmc", "baron_pancreas", "pbmc68k_zheng2017"],
        choices=sorted(DATASETS),
    )
    parser.add_argument("--n-repeats", type=int, default=1)
    parser.add_argument(
        "--run-label",
        default="default",
        help="Checkpoint label that distinguishes full-data draft and repeated-subsampling runs.",
    )
    parser.add_argument(
        "--subsample-fraction",
        type=float,
        default=1.0,
        help="Fraction of cells to use for each repeat; use 0.8 for manuscript-style subsampling pilots.",
    )
    parser.add_argument(
        "--ablation-ids",
        nargs="+",
        default=None,
        help="Optional subset of ablation IDs to run for faster P0 repeated checks.",
    )
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--max-pcs", type=int, default=50)
    parser.add_argument("--max-clusters", type=int, default=12)
    parser.add_argument("--embedding-stability-repeats", type=int, default=3)
    parser.add_argument("--random-state", type=int, default=20260502)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.force and DETAIL.exists():
        DETAIL.unlink()
    detail = run_detail(args)
    summary = summarize(detail)
    _atomic_write_tsv(summary, SUMMARY)
    _atomic_write_text(build_doc(summary, args), DOC)
    print(_rel(DETAIL))
    print(_rel(SUMMARY))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

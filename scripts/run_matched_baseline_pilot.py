#!/usr/bin/env python
"""Run local matched-baseline pilot checks for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-03
Purpose: Execute local Python baselines on the same 80% subsampling framework
used by the real-data ablation pilot, and import already-computed RMTGuard
pilot rows for matched annotation/batch comparison.
Data source: data/processed/*.h5ad and
results/ablation/realdata_ablation_annotation_detail.tsv.
Method notes: This is a pilot baseline layer. It does not execute Seurat v5 or
the official Seurat JackStraw workflow; those remain explicit blockers.
"""

from __future__ import annotations

import argparse
import csv
import math
import time
import tracemalloc
from pathlib import Path
from typing import Any

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
RMT_ABLATION_DETAIL = ROOT / "results" / "ablation" / "realdata_ablation_annotation_detail.tsv"
OUT_DIR = ROOT / "results" / "submission"
DETAIL = OUT_DIR / "matched_baseline_pilot_detail.tsv"
SUMMARY = OUT_DIR / "matched_baseline_pilot_summary.tsv"
BLOCKERS = OUT_DIR / "matched_baseline_external_blockers.tsv"
DOC = ROOT / "docs" / "matched_baseline_pilot.md"

RMT_SOURCE_RUN_LABEL = "subsample80_pilot10"
DEFAULT_RUN_LABEL = "matched_subsample80_pilot10"

DATASETS = {
    "kang_ifnb_pbmc": {
        "filename": "kang_ifnb_pbmc.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
        "label": "Kang IFN-beta PBMC",
    },
    "baron_pancreas": {
        "filename": "baron_pancreas.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
        "label": "Baron pancreas",
    },
    "pbmc68k_zheng2017": {
        "filename": "pbmc68k_zheng2017.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
        "label": "PBMC68k/Zheng 2017",
    },
    "pdac_gse263733": {
        "filename": "pdac_gse263733.h5ad",
        "label_key": "cell",
        "batch_key": "batch",
        "label": "PDAC GSE263733",
    },
}

RMT_METHOD_MAP = {
    "default_v3_3": {
        "method_id": "rmtguard_default_v3_3",
        "method_label": "RMTGuard default v3.3",
        "method_family": "RMTGuard",
    },
    "batch_residualized": {
        "method_id": "rmtguard_batch_residualized",
        "method_label": "RMTGuard batch residualized",
        "method_family": "RMTGuard ablation",
    },
    "force_min_embedding_pcs_10": {
        "method_id": "rmtguard_forced_min_10_pcs",
        "method_label": "RMTGuard forced min 10 PCs",
        "method_family": "negative control",
    },
}

LOCAL_BASELINES = {
    "scanpy_default_like": {
        "method_label": "Scanpy-like fixed 50 PCs",
        "method_family": "local Python baseline",
        "pc_rule": "fixed_50",
    },
    "fixed_pcs_30": {
        "method_label": "Fixed 30 PCs",
        "method_family": "local Python baseline",
        "pc_rule": "fixed_30",
    },
    "scanpy_elbow_rule": {
        "method_label": "Elbow-rule PCA",
        "method_family": "local Python baseline",
        "pc_rule": "elbow",
    },
    "parallel_analysis_pca": {
        "method_label": "Parallel-analysis PCA",
        "method_family": "local Python baseline",
        "pc_rule": "parallel_analysis",
    },
    "jackstraw_like_proxy": {
        "method_label": "JackStraw-like permutation proxy",
        "method_family": "local Python baseline",
        "pc_rule": "jackstraw_like_proxy",
    },
}

EXTERNAL_BLOCKERS = [
    {
        "method_id": "seurat_v5_default",
        "method_label": "Seurat v5 default",
        "execution_status": "blocked_external_dependency",
        "blocker": "R/Seurat v5 installation and h5ad-to-Seurat conversion must be verified in the author environment.",
    },
    {
        "method_id": "seurat_v5_jackstraw",
        "method_label": "Seurat v5 JackStraw PC rule",
        "execution_status": "blocked_runtime_and_dependency",
        "blocker": "Official Seurat JackStraw workflow is runtime-heavy and still needs R dependency, conversion, and matched split bookkeeping.",
    },
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


def _read_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, sep="\t")


def _key(row: dict[str, Any]) -> tuple[str, str, int, str]:
    return (
        str(row["dataset_id"]),
        str(row["method_id"]),
        int(row["repeat"]),
        str(row.get("run_label", DEFAULT_RUN_LABEL)),
    )


def _append(rows: list[dict[str, Any]], row: dict[str, Any]) -> None:
    rows.append(row)
    _atomic_write_tsv(pd.DataFrame(rows), DETAIL)


def _matrix(adata: ad.AnnData):
    return adata.layers["counts"] if "counts" in adata.layers else adata.X


def _to_dense(x) -> np.ndarray:
    if hasattr(x, "toarray"):
        x = x.toarray()
    return np.asarray(x, dtype=float)


def _normalize_log(x) -> np.ndarray:
    arr = _to_dense(x)
    totals = np.maximum(arr.sum(axis=1, keepdims=True), 1e-12)
    return np.log1p(arr / totals * 1e4)


def _select_top_variable(x_log: np.ndarray, max_genes: int) -> np.ndarray:
    if max_genes <= 0 or x_log.shape[1] <= max_genes:
        return x_log
    variances = np.var(x_log, axis=0)
    selected = np.argpartition(variances, -max_genes)[-max_genes:]
    selected = selected[np.argsort(variances[selected])[::-1]]
    return x_log[:, selected]


def _target_cluster_count(n_obs: int) -> int:
    return min(8, max(2, int(np.sqrt(max(n_obs, 2) / 2))))


def _safe_metric(labels_true, labels_pred, metric) -> float:
    labels_true = np.asarray(labels_true).astype(str)
    labels_pred = np.asarray(labels_pred).astype(str)
    if labels_true.size == 0 or np.unique(labels_true).size < 2:
        return math.nan
    if labels_pred.size == 0 or np.unique(labels_pred).size < 2:
        return math.nan
    return float(metric(labels_true, labels_pred))


def _choose_elbow_n_pcs(variance_ratio: np.ndarray, min_pcs: int = 5) -> int:
    variance_ratio = np.asarray(variance_ratio, dtype=float)
    n = variance_ratio.size
    if n == 0:
        return 0
    if n <= min_pcs:
        return int(n)
    cumulative = np.cumsum(variance_ratio)
    x = np.linspace(0.0, 1.0, n)
    y = (cumulative - cumulative[0]) / max(
        cumulative[-1] - cumulative[0], np.finfo(float).eps
    )
    distances = y - x
    start = max(0, min_pcs - 1)
    return int(np.argmax(distances[start:]) + start + 1)


def _count_contiguous_leading_passes(observed: np.ndarray, threshold: np.ndarray) -> int:
    passing = np.asarray(observed) > np.asarray(threshold)
    first_failed = np.flatnonzero(~passing)
    return int(first_failed[0]) if first_failed.size else int(passing.size)


def _parallel_analysis_n_pcs(
    x_scaled: np.ndarray,
    n_components: int,
    n_permutations: int,
    random_state: int,
    quantile: float,
) -> int:
    observed = PCA(n_components=n_components, random_state=random_state).fit(
        x_scaled
    ).explained_variance_
    rng = np.random.default_rng(random_state)
    null_values = np.zeros((max(1, n_permutations), n_components), dtype=float)
    for repeat in range(max(1, n_permutations)):
        order = np.argsort(rng.random(x_scaled.shape), axis=0)
        permuted = np.take_along_axis(x_scaled, order, axis=0)
        null_values[repeat] = PCA(
            n_components=n_components,
            random_state=random_state + repeat + 1,
        ).fit(permuted).explained_variance_
    threshold = np.quantile(null_values, quantile, axis=0)
    return _count_contiguous_leading_passes(observed, threshold)


def _baseline_labels(
    x,
    method_id: str,
    args: argparse.Namespace,
    seed: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    spec = LOCAL_BASELINES[method_id]
    start = time.perf_counter()
    tracemalloc.start()
    x_log = _select_top_variable(_normalize_log(x), args.baseline_hvg_n)
    x_scaled = StandardScaler().fit_transform(x_log)
    n_components = min(args.max_pcs, x_scaled.shape[0] - 1, x_scaled.shape[1])
    if n_components <= 0:
        labels = np.zeros(x_scaled.shape[0], dtype=int)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return labels, {
            "analysis_status": "baseline_no_pcs",
            "selected_pcs": 0,
            "embedding_pcs": 0,
            "pc_rule": spec["pc_rule"],
            "runtime_seconds": time.perf_counter() - start,
            "peak_memory_mb": peak / 1024 / 1024,
        }
    pca = PCA(n_components=n_components, random_state=seed).fit(x_scaled)
    pc_rule = spec["pc_rule"]
    if pc_rule == "fixed_50":
        selected_pcs = min(50, n_components)
    elif pc_rule == "fixed_30":
        selected_pcs = min(30, n_components)
    elif pc_rule == "elbow":
        selected_pcs = _choose_elbow_n_pcs(pca.explained_variance_ratio_, min_pcs=5)
    elif pc_rule == "parallel_analysis":
        selected_pcs = _parallel_analysis_n_pcs(
            x_scaled,
            n_components=n_components,
            n_permutations=args.baseline_permutations,
            random_state=seed,
            quantile=0.95,
        )
    elif pc_rule == "jackstraw_like_proxy":
        selected_pcs = _parallel_analysis_n_pcs(
            x_scaled,
            n_components=n_components,
            n_permutations=args.baseline_permutations,
            random_state=seed,
            quantile=0.99,
        )
    else:  # pragma: no cover - protected by method registry.
        raise ValueError(f"Unknown PC rule: {pc_rule}")
    embedding_pcs = min(max(1, int(selected_pcs)), n_components)
    pcs = pca.transform(x_scaled)[:, :embedding_pcs]
    labels = KMeans(
        n_clusters=_target_cluster_count(x_scaled.shape[0]),
        n_init=20,
        random_state=seed,
    ).fit_predict(pcs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return labels, {
        "analysis_status": "ok",
        "selected_pcs": int(selected_pcs),
        "embedding_pcs": int(embedding_pcs),
        "pc_rule": pc_rule,
        "baseline_hvg_n": int(min(args.baseline_hvg_n, x_log.shape[1])),
        "baseline_permutations": int(args.baseline_permutations)
        if pc_rule in {"parallel_analysis", "jackstraw_like_proxy"}
        else 0,
        "runtime_seconds": time.perf_counter() - start,
        "peak_memory_mb": peak / 1024 / 1024,
    }


def _split_indices(dataset_id: str, source_n_cells: int, repeat: int, args) -> np.ndarray:
    dataset_seed = sum(ord(ch) for ch in dataset_id)
    if args.subsample_fraction < 1.0:
        rng = np.random.default_rng(args.random_state + repeat * 997 + dataset_seed)
        subsample_n = max(2, int(round(source_n_cells * args.subsample_fraction)))
        return np.sort(rng.choice(source_n_cells, subsample_n, replace=False))
    return np.arange(source_n_cells)


def _import_rmt_rows(args: argparse.Namespace) -> pd.DataFrame:
    if not RMT_ABLATION_DETAIL.exists():
        return pd.DataFrame()
    source = pd.read_csv(RMT_ABLATION_DETAIL, sep="\t")
    source = source[
        (source["run_label"] == RMT_SOURCE_RUN_LABEL)
        & (source["dataset_id"].isin(args.datasets))
        & (source["ablation_id"].isin(RMT_METHOD_MAP))
        & (source["repeat"] < args.n_repeats)
    ].copy()
    rows: list[dict[str, Any]] = []
    for item in source.itertuples(index=False):
        mapping = RMT_METHOD_MAP[item.ablation_id]
        rows.append(
            {
                "run_label": args.run_label,
                "dataset_id": item.dataset_id,
                "dataset_label": DATASETS.get(item.dataset_id, {}).get(
                    "label", item.dataset_id
                ),
                "method_id": mapping["method_id"],
                "method_label": mapping["method_label"],
                "method_family": mapping["method_family"],
                "repeat": int(item.repeat),
                "execution_status": "imported_from_realdata_ablation",
                "n_cells": int(item.n_cells),
                "source_n_cells": int(item.source_n_cells),
                "subsample_n_cells": int(item.subsample_n_cells),
                "subsample_fraction": float(item.subsample_fraction),
                "n_genes": int(item.n_genes),
                "label_key": item.label_key,
                "batch_key": item.batch_key,
                "label_n": int(item.label_n),
                "batch_n": int(item.batch_n),
                "analysis_status": item.analysis_status,
                "no_call_reason": item.no_call_reason,
                "selected_pcs": int(item.n_embedding_pcs),
                "embedding_pcs": int(item.n_embedding_pcs),
                "pc_rule": str(getattr(item, "config_embedding_rule", "")),
                "cluster_n": int(item.cluster_n),
                "runtime_seconds": float(item.runtime_seconds),
                "peak_memory_mb": float(item.peak_memory_mb),
                "label_ari": float(item.label_ari),
                "label_nmi": float(item.label_nmi),
                "batch_ari": float(item.batch_ari)
                if pd.notna(item.batch_ari)
                else math.nan,
                "batch_nmi": float(item.batch_nmi)
                if pd.notna(item.batch_nmi)
                else math.nan,
                "source_table": _rel(RMT_ABLATION_DETAIL),
                "method_notes": "RMTGuard pilot metrics imported to avoid rerunning already-computed ablation rows.",
            }
        )
    return pd.DataFrame(rows)


def run_pilot(args: argparse.Namespace) -> pd.DataFrame:
    if args.force and DETAIL.exists():
        DETAIL.unlink()
    existing = _read_existing(DETAIL)
    imported = _import_rmt_rows(args)
    if existing.empty:
        rows = imported.to_dict(orient="records")
        if rows:
            _atomic_write_tsv(pd.DataFrame(rows), DETAIL)
    else:
        rows = existing.to_dict(orient="records")
        existing_keys = {_key(row) for row in rows}
        for row in imported.to_dict(orient="records"):
            if _key(row) not in existing_keys:
                rows.append(row)
                existing_keys.add(_key(row))
        _atomic_write_tsv(pd.DataFrame(rows), DETAIL)
    completed = {_key(row) for row in rows}

    methods = [method for method in args.methods if method in LOCAL_BASELINES]
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
        for repeat in range(args.n_repeats):
            idx = _split_indices(dataset_id, adata.n_obs, repeat, args)
            x = matrix_all[idx, :]
            labels_true = labels_all[idx]
            batches = batches_all[idx] if batches_all is not None else None
            for method_id in methods:
                plan = {
                    "run_label": args.run_label,
                    "dataset_id": dataset_id,
                    "method_id": method_id,
                    "repeat": repeat,
                }
                if _key(plan) in completed:
                    continue
                seed = (
                    args.random_state
                    + repeat * 101
                    + sum(ord(ch) for ch in dataset_id)
                    + sum(ord(ch) for ch in method_id)
                )
                labels_pred, metadata = _baseline_labels(x, method_id, args, seed)
                row = {
                    **plan,
                    "dataset_label": spec["label"],
                    "method_label": LOCAL_BASELINES[method_id]["method_label"],
                    "method_family": LOCAL_BASELINES[method_id]["method_family"],
                    "execution_status": "local_pilot_complete",
                    "n_cells": int(len(labels_true)),
                    "source_n_cells": int(adata.n_obs),
                    "subsample_n_cells": int(len(labels_true)),
                    "subsample_fraction": float(args.subsample_fraction),
                    "n_genes": int(adata.n_vars),
                    "label_key": spec["label_key"],
                    "batch_key": spec["batch_key"],
                    "label_n": int(pd.Series(labels_true).nunique()),
                    "batch_n": int(pd.Series(batches).nunique())
                    if batches is not None
                    else 0,
                    "no_call_reason": "",
                    "cluster_n": int(np.unique(labels_pred).size),
                    "label_ari": _safe_metric(
                        labels_true, labels_pred, adjusted_rand_score
                    ),
                    "label_nmi": _safe_metric(
                        labels_true, labels_pred, normalized_mutual_info_score
                    ),
                    "batch_ari": _safe_metric(
                        batches, labels_pred, adjusted_rand_score
                    )
                    if batches is not None
                    else math.nan,
                    "batch_nmi": _safe_metric(
                        batches, labels_pred, normalized_mutual_info_score
                    )
                    if batches is not None
                    else math.nan,
                    "source_table": "computed_by_run_matched_baseline_pilot.py",
                    "method_notes": "Local Python PCA/KMeans pilot baseline on matched subsampling split.",
                    **metadata,
                }
                _append(rows, row)
                completed.add(_key(row))
    return pd.DataFrame(rows)


def _mean_ci(values: pd.Series) -> tuple[float, float, float, float]:
    vals = pd.to_numeric(values, errors="coerce").dropna()
    if vals.empty:
        return math.nan, math.nan, math.nan, math.nan
    mean = float(vals.mean())
    sd = float(vals.std(ddof=1)) if len(vals) > 1 else math.nan
    if len(vals) == 1:
        return mean, mean, mean, sd
    margin = 1.96 * sd / math.sqrt(len(vals))
    return mean, mean - margin, mean + margin, sd


def summarize(detail: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    active = detail[detail["run_label"] == args.run_label].copy()
    rows: list[dict[str, Any]] = []
    for keys, group in active.groupby(
        ["dataset_id", "dataset_label", "method_id", "method_label", "method_family"],
        dropna=False,
    ):
        dataset_id, dataset_label, method_id, method_label, method_family = keys
        label_mean, label_low, label_high, label_sd = _mean_ci(group["label_ari"])
        batch_mean, batch_low, batch_high, batch_sd = _mean_ci(group["batch_ari"])
        nmi_mean, nmi_low, nmi_high, _ = _mean_ci(group["label_nmi"])
        rows.append(
            {
                "run_label": args.run_label,
                "dataset_id": dataset_id,
                "dataset_label": dataset_label,
                "method_id": method_id,
                "method_label": method_label,
                "method_family": method_family,
                "execution_status": ";".join(sorted(set(group["execution_status"]))),
                "n_repeats": int(group["repeat"].nunique()),
                "mean_label_ari": label_mean,
                "label_ari_ci95_low": label_low,
                "label_ari_ci95_high": label_high,
                "label_ari_sd": label_sd,
                "mean_label_nmi": nmi_mean,
                "label_nmi_ci95_low": nmi_low,
                "label_nmi_ci95_high": nmi_high,
                "mean_batch_ari": batch_mean,
                "batch_ari_ci95_low": batch_low,
                "batch_ari_ci95_high": batch_high,
                "batch_ari_sd": batch_sd,
                "mean_cluster_n": float(
                    pd.to_numeric(group["cluster_n"], errors="coerce").mean()
                ),
                "mean_selected_pcs": float(
                    pd.to_numeric(group["selected_pcs"], errors="coerce").mean()
                ),
                "no_call_rate": float(
                    (group["analysis_status"].astype(str) == "diagnostic_no_call").mean()
                ),
                "mean_runtime_seconds": float(
                    pd.to_numeric(group["runtime_seconds"], errors="coerce").mean()
                ),
                "mean_peak_memory_mb": float(
                    pd.to_numeric(group["peak_memory_mb"], errors="coerce").mean()
                ),
            }
        )
    return pd.DataFrame(rows).sort_values(["dataset_id", "method_family", "method_id"])


def build_blockers(args: argparse.Namespace) -> pd.DataFrame:
    rows = []
    for dataset_id in args.datasets:
        for blocker in EXTERNAL_BLOCKERS:
            rows.append(
                {
                    "run_label": args.run_label,
                    "dataset_id": dataset_id,
                    "dataset_label": DATASETS[dataset_id]["label"],
                    **blocker,
                    "required_for_20_50_route": True,
                }
            )
    return pd.DataFrame(rows)


def _fmt(mean: float, low: float, high: float) -> str:
    if not np.isfinite(mean):
        return "NA"
    return f"{mean:.3f} ({low:.3f} to {high:.3f})"


def build_doc(summary: pd.DataFrame, blockers: pd.DataFrame, args: argparse.Namespace) -> str:
    lines = [
        "# Matched baseline pilot",
        "",
        "Generated by `python scripts/run_matched_baseline_pilot.py`.",
        "",
        "## Evidence Boundary",
        "",
        "- This is a local Python matched-baseline pilot on the same 80% subsampling repeat framework.",
        "- RMTGuard rows are imported from the already-computed real-data ablation pilot.",
        "- Seurat v5 default and official Seurat JackStraw are not executed here and remain blockers.",
        "- These results do not reopen the Nature Methods route by themselves.",
        "",
        "## Pilot Coverage",
        "",
        f"- Datasets: `{summary['dataset_id'].nunique()}`",
        f"- Executed/imported methods: `{summary['method_id'].nunique()}`",
        f"- Repeats per completed method: target `{args.n_repeats}`",
        f"- External blocked rows: `{len(blockers)}`",
        "",
        "## Dataset-level Label ARI Summary",
        "",
        "| Dataset | Best local/imported method by label ARI | Label ARI (95% CI) | RMTGuard default label ARI (95% CI) | Note |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for dataset_id, group in summary.groupby("dataset_id", sort=False):
        ranked = group.sort_values("mean_label_ari", ascending=False)
        best = ranked.iloc[0]
        default = group[group["method_id"] == "rmtguard_default_v3_3"]
        default_text = "NA"
        if not default.empty:
            default_row = default.iloc[0]
            default_text = _fmt(
                default_row["mean_label_ari"],
                default_row["label_ari_ci95_low"],
                default_row["label_ari_ci95_high"],
            )
        note = (
            "diagnostic no-call stress context; forced clustering is not a rescue"
            if dataset_id == "pbmc68k_zheng2017"
            else "pilot comparison only; requires Seurat/JackStraw execution"
        )
        if str(best["method_family"]) == "negative control":
            note = (
                "best row is a forced-PC negative control; report as sensitivity "
                "evidence, not as the recommended method"
            )
        lines.append(
            f"| {best['dataset_label']} | {best['method_label']} | {_fmt(best['mean_label_ari'], best['label_ari_ci95_low'], best['label_ari_ci95_high'])} | {default_text} | {note} |"
        )

    lines.extend(
        [
            "",
            "## External Baseline Blockers",
            "",
            "| Method | Status | Blocker |",
            "| --- | --- | --- |",
        ]
    )
    for row in blockers.drop_duplicates(["method_id"]).itertuples(index=False):
        lines.append(f"| {row.method_label} | `{row.execution_status}` | {row.blocker} |")
    lines.extend(
        [
            "",
            "## Generated Artifacts",
            "",
            f"- Detail TSV: `{_rel(DETAIL)}`",
            f"- Summary TSV: `{_rel(SUMMARY)}`",
            f"- External blocker TSV: `{_rel(BLOCKERS)}`",
            "",
            "## Next Step",
            "",
            "Use this pilot to drive the final matched-baseline execution: add Seurat v5 and official JackStraw rows, then scale to 20-50 repeats with paired statistical tests and multiple-testing correction.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run local matched-baseline pilot checks."
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=list(DATASETS),
        choices=sorted(DATASETS),
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=list(LOCAL_BASELINES),
        choices=sorted(LOCAL_BASELINES),
    )
    parser.add_argument("--run-label", default=DEFAULT_RUN_LABEL)
    parser.add_argument("--processed-dir", type=Path, default=PROCESSED)
    parser.add_argument("--n-repeats", type=int, default=10)
    parser.add_argument("--subsample-fraction", type=float, default=0.8)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument("--max-pcs", type=int, default=50)
    parser.add_argument("--baseline-hvg-n", type=int, default=2000)
    parser.add_argument("--baseline-permutations", type=int, default=5)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    detail = run_pilot(args)
    summary = summarize(detail, args)
    blockers = build_blockers(args)
    _atomic_write_tsv(summary, SUMMARY)
    _atomic_write_tsv(blockers, BLOCKERS)
    _atomic_write_text(build_doc(summary, blockers, args), DOC)
    print(_rel(DETAIL))
    print(_rel(SUMMARY))
    print(_rel(BLOCKERS))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

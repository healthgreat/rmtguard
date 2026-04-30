from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from rmtguard import RMTGuard, RMTGuardConfig
from rmtguard.cluster import graph_modularity_labels


ROOT = Path(__file__).resolve().parents[1]


def _safe_metric(labels_true, labels_pred, metric):
    labels_true = np.asarray(labels_true).astype(str)
    if labels_true.size == 0 or np.unique(labels_true).size < 2:
        return float("nan")
    return float(metric(labels_true, np.asarray(labels_pred).astype(str)))


def _as_dense_array(x) -> np.ndarray:
    if hasattr(x, "toarray"):
        x = x.toarray()
    return np.asarray(x, dtype=float)


def _choose_elbow_n_pcs(variance_ratio: np.ndarray, min_pcs: int = 5) -> int:
    """Select PCs by maximum distance from the cumulative-variance chord."""

    variance_ratio = np.asarray(variance_ratio, dtype=float)
    n = variance_ratio.size
    if n == 0:
        return 0
    if n <= min_pcs:
        return int(n)
    cumulative = np.cumsum(variance_ratio)
    x = np.linspace(0.0, 1.0, n)
    y = (cumulative - cumulative[0]) / max(cumulative[-1] - cumulative[0], np.finfo(float).eps)
    chord = x
    distances = y - chord
    start = max(0, min_pcs - 1)
    return int(np.argmax(distances[start:]) + start + 1)


def _count_contiguous_leading_passes(observed: np.ndarray, threshold: np.ndarray) -> int:
    passing = np.asarray(observed) > np.asarray(threshold)
    first_failed = np.flatnonzero(~passing)
    return int(first_failed[0]) if first_failed.size else int(passing.size)


def _choose_parallel_analysis_n_pcs(
    scaled: np.ndarray,
    max_pcs: int,
    n_permutations: int,
    random_state: int,
    quantile: float = 0.95,
) -> int:
    """Select PCs whose variances exceed a column-permutation null."""

    scaled = _as_dense_array(scaled)
    n_components = min(max_pcs, scaled.shape[0] - 1, scaled.shape[1])
    if n_components <= 0:
        return 0
    observed = PCA(n_components=n_components, random_state=random_state).fit(scaled).explained_variance_
    rng = np.random.default_rng(random_state)
    null_values = np.zeros((max(1, n_permutations), n_components), dtype=float)
    for repeat in range(max(1, n_permutations)):
        permuted = scaled.copy()
        for col in range(permuted.shape[1]):
            rng.shuffle(permuted[:, col])
        null_values[repeat] = PCA(n_components=n_components, random_state=random_state + repeat + 1).fit(permuted).explained_variance_
    threshold = np.quantile(null_values, quantile, axis=0)
    return _count_contiguous_leading_passes(observed, threshold)


def _prepare_scanpy_pca(adata, max_pcs: int, random_state: int):
    import scanpy as sc

    work = adata.copy()
    if "counts" in work.layers:
        work.X = work.layers["counts"].copy()
    sc.pp.normalize_total(work, target_sum=1e4)
    sc.pp.log1p(work)
    sc.pp.highly_variable_genes(work, n_top_genes=min(2000, work.n_vars), flavor="seurat")
    if "highly_variable" in work.var and work.var["highly_variable"].sum() > 0:
        work = work[:, work.var["highly_variable"]].copy()
    sc.pp.scale(work, max_value=10)
    n_components = min(max_pcs, work.n_obs - 1, work.n_vars - 1)
    sc.tl.pca(work, n_comps=n_components, random_state=random_state)
    return work, n_components


def _scanpy_fixed_baseline(adata, n_pcs: int, label_key: str | None, random_state: int) -> dict:
    work, n_components = _prepare_scanpy_pca(adata, n_pcs, random_state)
    labels = graph_modularity_labels(work.obsm["X_pca"][:, :n_components], n_neighbors=15, resolution=1.0)
    return {
        "method": f"fixed_pcs_{n_pcs}",
        "n_signal_pcs": n_components,
        "baseline_pc_rule": f"fixed_{n_pcs}",
        "cluster_n": int(np.unique(labels).size),
        "baseline_clusterer": "graph_modularity",
        "baseline_resolution": 1.0,
        "baseline_n_neighbors": 15,
        "ari": _safe_metric(work.obs[label_key], labels, adjusted_rand_score) if label_key else float("nan"),
        "nmi": _safe_metric(work.obs[label_key], labels, normalized_mutual_info_score) if label_key else float("nan"),
    }


def _scanpy_default_baseline(adata, label_key: str | None, random_state: int) -> dict:
    baseline = _scanpy_fixed_baseline(adata, n_pcs=50, label_key=label_key, random_state=random_state)
    baseline["method"] = "scanpy_default_like"
    return baseline


def _scanpy_pc_rule_baseline(
    adata,
    method: str,
    label_key: str | None,
    random_state: int,
    max_pcs: int,
    n_permutations: int,
) -> dict:
    work, n_components = _prepare_scanpy_pca(adata, max_pcs, random_state)
    variance_ratio = np.asarray(work.uns["pca"]["variance_ratio"], dtype=float)
    if method == "elbow_rule":
        selected = _choose_elbow_n_pcs(variance_ratio, min_pcs=5)
        rule = "curvature_elbow"
    elif method == "parallel_analysis":
        selected = _choose_parallel_analysis_n_pcs(work.X, max_pcs=n_components, n_permutations=n_permutations, random_state=random_state)
        rule = "column_permutation_parallel_analysis"
    elif method == "jackstraw_like":
        selected = _choose_parallel_analysis_n_pcs(work.X, max_pcs=n_components, n_permutations=n_permutations, random_state=random_state, quantile=0.99)
        rule = "jackstraw_like_gene_permutation"
    else:
        raise ValueError(f"Unknown baseline method: {method}")
    selected_for_embedding = min(max(1, selected), n_components)
    labels = graph_modularity_labels(work.obsm["X_pca"][:, :selected_for_embedding], n_neighbors=15, resolution=1.0)
    return {
        "method": method,
        "n_signal_pcs": int(selected),
        "n_embedding_pcs": int(selected_for_embedding),
        "baseline_pc_rule": rule,
        "baseline_n_permutations": int(n_permutations) if method in {"parallel_analysis", "jackstraw_like"} else 0,
        "cluster_n": int(np.unique(labels).size),
        "baseline_clusterer": "graph_modularity",
        "baseline_resolution": 1.0,
        "baseline_n_neighbors": 15,
        "ari": _safe_metric(work.obs[label_key], labels, adjusted_rand_score) if label_key else float("nan"),
        "nmi": _safe_metric(work.obs[label_key], labels, normalized_mutual_info_score) if label_key else float("nan"),
    }


def _run_rmtguard(adata, dataset_id: str, label_key: str | None, batch_key: str | None, args) -> tuple[dict, dict]:
    matrix = adata.layers["counts"] if "counts" in adata.layers else adata.X
    batches = adata.obs[batch_key].to_numpy() if batch_key and batch_key in adata.obs else None
    result = RMTGuard(
        RMTGuardConfig(
            hvg_grid=tuple(args.hvg_grid),
            max_pcs=args.max_pcs,
            min_embedding_pcs=args.min_embedding_pcs,
            whiten=args.whiten,
            pc_rule=args.pc_rule,
            hvg_rule=args.hvg_rule,
            hvg_score=args.hvg_score,
            embedding_rule=args.embedding_rule,
            embedding_source=args.embedding_source,
            near_edge_window=args.near_edge_window,
            embedding_stability_repeats=args.embedding_stability_repeats,
            embedding_stability_threshold=args.embedding_stability_threshold,
            embedding_subsample_fraction=args.embedding_subsample_fraction,
            low_signal_rescue_rule=args.low_signal_rescue_rule,
            low_signal_rescue_max_pcs=args.low_signal_rescue_max_pcs,
            low_signal_rescue_min_pcs=args.low_signal_rescue_min_pcs,
            low_signal_rescue_stability_threshold=args.low_signal_rescue_stability_threshold,
            resolution_rule=args.resolution_rule,
            graph_resolution_grid=tuple(args.graph_resolution_grid),
            low_signal_graph_resolution=args.low_signal_graph_resolution,
            low_signal_pc_threshold=args.low_signal_pc_threshold,
            high_signal_graph_resolution=args.high_signal_graph_resolution,
            high_signal_pc_threshold=args.high_signal_pc_threshold,
            n_permutations=args.n_permutations,
            tw_alpha=args.tw_alpha,
            stability_repeats=args.stability_repeats,
            random_state=args.random_state,
            cluster_grid=tuple(range(2, args.max_clusters + 1)),
            batch_key=batch_key,
        )
    ).fit(
        matrix,
        batches=batches,
        benchmark_metadata={"dataset_id": dataset_id, "label_key": label_key, "batch_key": batch_key},
    )
    row = {
        "method": "rmtguard",
        "n_signal_pcs": result.n_signal_pcs,
        "n_embedding_pcs": result.n_embedding_pcs,
        "strict_signal_pcs": result.embedding_diagnostics["strict_signal_pcs"],
        "near_edge_candidate_pcs": result.embedding_diagnostics["near_edge_candidate_pcs"],
        "low_signal_candidate_pcs": result.embedding_diagnostics["low_signal_candidate_pcs"],
        "accepted_low_signal_rescue_pcs": result.embedding_diagnostics["accepted_low_signal_rescue_pcs"],
        "accepted_embedding_pcs": result.embedding_diagnostics["accepted_embedding_pcs"],
        "embedding_rule": result.embedding_diagnostics["rule"],
        "embedding_source": result.embedding_diagnostics["source"],
        "low_signal_rescue_rule": result.embedding_diagnostics["low_signal_rescue_rule"],
        "embedding_pc_stability_min": result.embedding_diagnostics["embedding_pc_stability_min"],
        "embedding_pc_stability_median": result.embedding_diagnostics["embedding_pc_stability_median"],
        "selected_hvg_n": result.selected_hvg_n,
        "cluster_n": result.cluster_n,
        "n_neighbors": result.n_neighbors,
        "mp_edge": result.mp_edge,
        "selected_edge": result.pc_diagnostics["selected_edge"],
        "bulk_ks": result.bulk_ks,
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
        "runtime_seconds": result.benchmark_metadata["runtime_seconds"],
        "peak_memory_mb": result.benchmark_metadata["peak_memory_mb"],
        "ari": _safe_metric(adata.obs[label_key], result.cluster_labels, adjusted_rand_score) if label_key else float("nan"),
        "nmi": _safe_metric(adata.obs[label_key], result.cluster_labels, normalized_mutual_info_score) if label_key else float("nan"),
    }
    detail = {
        "pc_diagnostics": result.pc_diagnostics,
        "hvg_diagnostics": result.hvg_diagnostics,
        "embedding_diagnostics": result.embedding_diagnostics,
        "resolution_scan": result.resolution_scan,
        "null_calibration": result.null_calibration,
        "benchmark_metadata": result.benchmark_metadata,
    }
    return row, detail


def run_dataset(path: Path, dataset_id: str, label_key: str | None, batch_key: str | None, args) -> tuple[list[dict], dict]:
    import scanpy as sc

    adata = sc.read_h5ad(path)
    rows = []
    detail: dict = {"dataset_id": dataset_id, "n_cells": int(adata.n_obs), "n_genes": int(adata.n_vars)}
    rmt_row, rmt_detail = _run_rmtguard(adata, dataset_id, label_key, batch_key, args)
    rows.append({"dataset_id": dataset_id, **rmt_row})
    detail["rmtguard"] = rmt_detail
    rows.append({"dataset_id": dataset_id, **_scanpy_default_baseline(adata, label_key, args.random_state)})
    rows.append({"dataset_id": dataset_id, **_scanpy_fixed_baseline(adata, 30, label_key, args.random_state)})
    rows.append({"dataset_id": dataset_id, **_scanpy_fixed_baseline(adata, 50, label_key, args.random_state)})
    for method in args.additional_baselines:
        rows.append(
            {
                "dataset_id": dataset_id,
                **_scanpy_pc_rule_baseline(
                    adata,
                    method,
                    label_key,
                    args.random_state,
                    max_pcs=args.max_pcs,
                    n_permutations=args.baseline_permutations,
                ),
            }
        )
    return rows, detail


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 1 PBMC benchmarks for RMTGuard.")
    parser.add_argument("--processed-dir", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "phase1_benchmarks")
    parser.add_argument("--datasets", nargs="+", default=["pbmc3k_10x", "kang_ifnb_pbmc"])
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--max-pcs", type=int, default=50)
    parser.add_argument("--min-embedding-pcs", type=int, default=0)
    parser.add_argument("--whiten", default="biwhiten", choices=["biwhiten", "zscore"])
    parser.add_argument("--max-clusters", type=int, default=12)
    parser.add_argument("--pc-rule", default="mp_tw", choices=["mp", "mp_tw", "permutation", "mp_tw_permutation"])
    parser.add_argument("--hvg-rule", default="spectral_stability", choices=["spectral_plateau", "spectral_stability", "dispersion"])
    parser.add_argument("--hvg-score", default="normalized_dispersion", choices=["raw_dispersion", "normalized_dispersion"])
    parser.add_argument("--embedding-rule", default="adaptive_near_edge", choices=["adaptive_near_edge", "strict_signal"])
    parser.add_argument("--embedding-source", default="standard_pca", choices=["standard_pca", "rmt_scores"])
    parser.add_argument("--near-edge-window", type=float, default=1.25)
    parser.add_argument("--embedding-stability-repeats", type=int, default=5)
    parser.add_argument("--embedding-stability-threshold", type=float, default=0.75)
    parser.add_argument("--embedding-subsample-fraction", type=float, default=0.80)
    parser.add_argument("--low-signal-rescue-rule", default="off", choices=["off", "stable_embedding"])
    parser.add_argument("--low-signal-rescue-max-pcs", type=int, default=12)
    parser.add_argument("--low-signal-rescue-min-pcs", type=int, default=2)
    parser.add_argument("--low-signal-rescue-stability-threshold", type=float, default=0.90)
    parser.add_argument("--resolution-rule", default="graph_modularity", choices=["graph_modularity", "kmeans_stability", "consensus_stability"])
    parser.add_argument("--graph-resolution-grid", type=float, nargs="+", default=[1.0])
    parser.add_argument("--low-signal-graph-resolution", type=float, default=1.0)
    parser.add_argument("--low-signal-pc-threshold", type=int, default=3)
    parser.add_argument("--high-signal-graph-resolution", type=float, default=1.5)
    parser.add_argument("--high-signal-pc-threshold", type=int, default=10)
    parser.add_argument("--n-permutations", type=int, default=0)
    parser.add_argument("--tw-alpha", type=float, default=0.01)
    parser.add_argument("--stability-repeats", type=int, default=5)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument(
        "--additional-baselines",
        nargs="+",
        default=["elbow_rule", "parallel_analysis", "jackstraw_like"],
        choices=["elbow_rule", "parallel_analysis", "jackstraw_like"],
    )
    parser.add_argument("--baseline-permutations", type=int, default=20)
    args = parser.parse_args()

    dataset_specs = {
        "pbmc3k_10x": {"path": args.processed_dir / "pbmc3k_10x.h5ad", "label_key": None, "batch_key": "batch"},
        "kang_ifnb_pbmc": {"path": args.processed_dir / "kang_ifnb_pbmc.h5ad", "label_key": "cell", "batch_key": "batch"},
        "baron_pancreas": {"path": args.processed_dir / "baron_pancreas.h5ad", "label_key": "cell", "batch_key": "batch"},
        "pbmc68k_zheng2017": {"path": args.processed_dir / "pbmc68k_zheng2017.h5ad", "label_key": "cell", "batch_key": "batch"},
    }

    args.outdir.mkdir(parents=True, exist_ok=True)
    all_rows = []
    details = {}
    for dataset_id in args.datasets:
        spec = dataset_specs[dataset_id]
        if not spec["path"].exists():
            raise FileNotFoundError(f"Prepared dataset not found: {spec['path']}. Run scripts/prepare_phase1_datasets.py first.")
        rows, detail = run_dataset(spec["path"], dataset_id, spec["label_key"], spec["batch_key"], args)
        all_rows.extend(rows)
        details[dataset_id] = detail

    summary_path = args.outdir / "phase1_benchmark_summary.tsv"
    fieldnames = sorted({key for row in all_rows for key in row})
    with summary_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(all_rows)

    details_path = args.outdir / "phase1_benchmark_details.json"
    with details_path.open("w", encoding="utf-8") as handle:
        json.dump(details, handle, indent=2)

    print(summary_path)
    print(details_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

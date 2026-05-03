from __future__ import annotations

import argparse
import csv
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score
from sklearn.preprocessing import StandardScaler

from rmtguard import RMTGuard, RMTGuardConfig


ROOT = Path(__file__).resolve().parents[1]

DATASET_FILENAMES = {
    "pbmc3k_10x": "pbmc3k_10x.h5ad",
    "paul15_hematopoiesis": "paul15_hematopoiesis.h5ad",
    "kang_ifnb_pbmc": "kang_ifnb_pbmc.h5ad",
    "baron_pancreas": "baron_pancreas.h5ad",
    "pbmc68k_zheng2017": "pbmc68k_zheng2017.h5ad",
    "pdac_gse154778": "pdac_gse154778.h5ad",
    "pdac_gse263733": "pdac_gse263733.h5ad",
}


def _target_cluster_count(n_obs: int) -> int:
    return min(8, max(2, int(np.sqrt(max(n_obs, 2) / 2))))


def _read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row})
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    tmp.replace(path)


def _normalize_log(x) -> np.ndarray:
    if hasattr(x, "toarray"):
        x = x.toarray()
    arr = np.asarray(x, dtype=float)
    totals = np.maximum(arr.sum(axis=1, keepdims=True), 1e-12)
    return np.log1p(arr / totals * 1e4)


def _fixed_pca_labels(x, n_pcs: int, random_state: int) -> np.ndarray:
    x_log = _normalize_log(x)
    x_scaled = StandardScaler().fit_transform(x_log)
    n_components = min(n_pcs, x_scaled.shape[0] - 1, x_scaled.shape[1])
    pcs = PCA(n_components=n_components, random_state=random_state).fit_transform(x_scaled)
    return KMeans(
        n_clusters=_target_cluster_count(x_scaled.shape[0]),
        n_init=20,
        random_state=random_state,
    ).fit_predict(pcs)


def _choose_elbow_n_pcs(variance_ratio: np.ndarray, min_pcs: int = 5) -> int:
    variance_ratio = np.asarray(variance_ratio, dtype=float)
    n = variance_ratio.size
    if n == 0:
        return 0
    if n <= min_pcs:
        return int(n)
    cumulative = np.cumsum(variance_ratio)
    x = np.linspace(0.0, 1.0, n)
    y = (cumulative - cumulative[0]) / max(cumulative[-1] - cumulative[0], np.finfo(float).eps)
    distances = y - x
    start = max(0, min_pcs - 1)
    return int(np.argmax(distances[start:]) + start + 1)


def _count_contiguous_leading_passes(observed: np.ndarray, threshold: np.ndarray) -> int:
    passing = np.asarray(observed) > np.asarray(threshold)
    first_failed = np.flatnonzero(~passing)
    return int(first_failed[0]) if first_failed.size else int(passing.size)


def _choose_parallel_analysis_n_pcs(
    x_scaled: np.ndarray,
    max_pcs: int,
    n_permutations: int,
    random_state: int,
    quantile: float = 0.95,
) -> int:
    n_components = min(max_pcs, x_scaled.shape[0] - 1, x_scaled.shape[1])
    if n_components <= 0:
        return 0
    observed = PCA(n_components=n_components, random_state=random_state).fit(x_scaled).explained_variance_
    rng = np.random.default_rng(random_state)
    null_values = np.zeros((max(1, n_permutations), n_components), dtype=float)
    for repeat in range(max(1, n_permutations)):
        permuted = x_scaled.copy()
        for col in range(permuted.shape[1]):
            rng.shuffle(permuted[:, col])
        null_values[repeat] = PCA(n_components=n_components, random_state=random_state + repeat + 1).fit(permuted).explained_variance_
    threshold = np.quantile(null_values, quantile, axis=0)
    return _count_contiguous_leading_passes(observed, threshold)


def _pc_rule_pca_labels(x, method: str, args, random_state: int) -> tuple[np.ndarray, dict]:
    x_log = _normalize_log(x)
    x_scaled = StandardScaler().fit_transform(x_log)
    n_components = min(args.max_pcs, x_scaled.shape[0] - 1, x_scaled.shape[1])
    if n_components <= 0:
        return np.zeros(x_scaled.shape[0], dtype=int), {"baseline_selected_pcs": 0, "baseline_pc_rule": method}
    pca = PCA(n_components=n_components, random_state=random_state).fit(x_scaled)
    if method == "elbow_rule":
        selected = _choose_elbow_n_pcs(pca.explained_variance_ratio_, min_pcs=5)
        rule = "curvature_elbow"
    elif method == "parallel_analysis":
        selected = _choose_parallel_analysis_n_pcs(
            x_scaled,
            max_pcs=n_components,
            n_permutations=args.baseline_permutations,
            random_state=random_state,
        )
        rule = "column_permutation_parallel_analysis"
    elif method == "jackstraw_like":
        selected = _choose_parallel_analysis_n_pcs(
            x_scaled,
            max_pcs=n_components,
            n_permutations=args.baseline_permutations,
            random_state=random_state,
            quantile=0.99,
        )
        rule = "jackstraw_like_gene_permutation"
    else:
        raise ValueError(f"Unknown PC-rule baseline: {method}")
    selected_for_embedding = min(max(1, selected), n_components)
    pcs = pca.transform(x_scaled)[:, :selected_for_embedding]
    labels = KMeans(
        n_clusters=_target_cluster_count(x_scaled.shape[0]),
        n_init=20,
        random_state=random_state,
    ).fit_predict(pcs)
    return labels, {
        "baseline_selected_pcs": int(selected),
        "baseline_embedding_pcs": int(selected_for_embedding),
        "baseline_pc_rule": rule,
        "baseline_n_permutations": int(args.baseline_permutations) if method in {"parallel_analysis", "jackstraw_like"} else 0,
    }


def _coarse_pca_labels(x, args, random_state: int) -> tuple[np.ndarray, dict]:
    """Build a label-free coarse partition before within-compartment RMTGuard."""

    x_log = _normalize_log(x)
    x_scaled = StandardScaler().fit_transform(x_log)
    max_pcs = min(args.coarse_max_pcs, args.max_pcs)
    n_components = min(max_pcs, x_scaled.shape[0] - 1, x_scaled.shape[1])
    if n_components <= 0:
        return np.zeros(x_scaled.shape[0], dtype=int), {
            "coarse_pc_rule": args.coarse_pc_rule,
            "coarse_selected_pcs": 0,
            "coarse_embedding_pcs": 0,
            "coarse_cluster_n": 1,
        }

    pca = PCA(n_components=n_components, random_state=random_state).fit(x_scaled)
    if args.coarse_pc_rule == "elbow_rule":
        selected = _choose_elbow_n_pcs(pca.explained_variance_ratio_, min_pcs=args.coarse_min_pcs)
        rule = "curvature_elbow"
    elif args.coarse_pc_rule == "parallel_analysis":
        selected = _choose_parallel_analysis_n_pcs(
            x_scaled,
            max_pcs=n_components,
            n_permutations=args.baseline_permutations,
            random_state=random_state,
        )
        rule = "column_permutation_parallel_analysis"
    else:
        raise ValueError(f"Unknown coarse PC rule: {args.coarse_pc_rule}")

    selected_for_embedding = min(max(1, selected), n_components)
    pcs = pca.transform(x_scaled)[:, :selected_for_embedding]
    n_clusters = min(args.coarse_max_clusters, _target_cluster_count(x_scaled.shape[0]), x_scaled.shape[0])
    if n_clusters <= 1:
        labels = np.zeros(x_scaled.shape[0], dtype=int)
    else:
        labels = KMeans(
            n_clusters=n_clusters,
            n_init=20,
            random_state=random_state,
        ).fit_predict(pcs)
    return labels, {
        "coarse_pc_rule": rule,
        "coarse_selected_pcs": int(selected),
        "coarse_embedding_pcs": int(selected_for_embedding),
        "coarse_cluster_n": int(np.unique(labels).size),
    }


def _fit_rmtguard(
    x,
    args,
    seed: int,
    resolution_rule: str | None = None,
    embedding_rule: str | None = None,
):
    return RMTGuard(
        RMTGuardConfig(
            hvg_grid=tuple(args.hvg_grid),
            max_pcs=args.max_pcs,
            min_embedding_pcs=args.min_embedding_pcs,
            whiten=args.whiten,
            pc_rule=args.pc_rule,
            hvg_rule=args.hvg_rule,
            hvg_score=args.hvg_score,
            embedding_rule=embedding_rule or args.embedding_rule,
            embedding_source=args.embedding_source,
            near_edge_window=args.near_edge_window,
            embedding_stability_repeats=args.embedding_stability_repeats,
            embedding_stability_threshold=args.embedding_stability_threshold,
            embedding_subsample_fraction=args.embedding_subsample_fraction,
            low_signal_rescue_rule=args.low_signal_rescue_rule,
            low_signal_rescue_max_pcs=args.low_signal_rescue_max_pcs,
            low_signal_rescue_min_pcs=args.low_signal_rescue_min_pcs,
            low_signal_rescue_stability_threshold=args.low_signal_rescue_stability_threshold,
            low_signal_rescue_null_permutations=args.low_signal_rescue_null_permutations,
            low_signal_rescue_null_quantile=args.low_signal_rescue_null_quantile,
            low_signal_rescue_min_eigen_ratio=args.low_signal_rescue_min_eigen_ratio,
            resolution_rule=resolution_rule or args.resolution_rule,
            graph_resolution_grid=tuple(args.graph_resolution_grid),
            low_signal_graph_resolution=args.low_signal_graph_resolution,
            low_signal_pc_threshold=args.low_signal_pc_threshold,
            high_signal_graph_resolution=args.high_signal_graph_resolution,
            high_signal_pc_threshold=args.high_signal_pc_threshold,
            n_permutations=args.n_permutations,
            tw_alpha=args.tw_alpha,
            stability_repeats=args.stability_repeats,
            random_state=seed,
            cluster_grid=tuple(range(2, args.max_clusters + 1)),
        )
    ).fit(x)


def _rmtguard_metadata(result, args, resolution_rule: str) -> dict:
    embedding_diag = result.embedding_diagnostics
    return {
        "selected_hvg_n": int(result.selected_hvg_n),
        "n_signal_pcs": int(result.n_signal_pcs),
        "n_embedding_pcs": int(result.n_embedding_pcs),
        "strict_signal_pcs": int(embedding_diag.get("strict_signal_pcs", result.n_signal_pcs)),
        "near_edge_candidate_pcs": int(embedding_diag.get("near_edge_candidate_pcs", 0)),
        "low_signal_candidate_pcs": int(embedding_diag.get("low_signal_candidate_pcs", 0)),
        "accepted_low_signal_rescue_pcs": int(embedding_diag.get("accepted_low_signal_rescue_pcs", 0)),
        "accepted_embedding_pcs": int(embedding_diag.get("accepted_embedding_pcs", result.n_embedding_pcs)),
        "embedding_rule": embedding_diag.get("rule", args.embedding_rule),
        "embedding_source": embedding_diag.get("source", args.embedding_source),
        "low_signal_rescue_rule": embedding_diag.get("low_signal_rescue_rule", args.low_signal_rescue_rule),
        "low_signal_rescue_null_permutations": embedding_diag.get("low_signal_rescue_null_permutations", args.low_signal_rescue_null_permutations),
        "low_signal_rescue_null_quantile": embedding_diag.get("low_signal_rescue_null_quantile", args.low_signal_rescue_null_quantile),
        "low_signal_rescue_min_eigen_ratio": embedding_diag.get("low_signal_rescue_min_eigen_ratio", args.low_signal_rescue_min_eigen_ratio),
        "embedding_pc_stability_min": embedding_diag.get("embedding_pc_stability_min", ""),
        "embedding_pc_stability_median": embedding_diag.get("embedding_pc_stability_median", ""),
        "n_neighbors": int(result.n_neighbors) if result.n_neighbors is not None else "",
        "rmtguard_selected_cluster_n": int(result.cluster_n) if result.cluster_n is not None else "",
        "resolution_rule": resolution_rule,
        "hvg_rule": args.hvg_rule,
        "hvg_score": args.hvg_score,
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
    }


def _rmtguard_run(x, args, seed: int) -> tuple[np.ndarray, dict]:
    result = _fit_rmtguard(x, args, seed)
    return result.cluster_labels, _rmtguard_metadata(result, args, args.resolution_rule)


def _rmtguard_fixed_k_run(x, args, seed: int) -> tuple[np.ndarray, dict]:
    result = _fit_rmtguard(x, args, seed, resolution_rule="kmeans_stability")
    metadata = _rmtguard_metadata(result, args, "fixed_k_on_rmtguard_embedding")
    if result.embedding.shape[1] == 0:
        return result.cluster_labels, metadata
    labels = KMeans(
        n_clusters=args.fixed_k,
        n_init=20,
        random_state=seed,
    ).fit_predict(result.embedding)
    return labels, metadata


def _rmtguard_strict_signal_run(x, args, seed: int) -> tuple[np.ndarray, dict]:
    result = _fit_rmtguard(x, args, seed, embedding_rule="strict_signal")
    return result.cluster_labels, _rmtguard_metadata(result, args, args.resolution_rule)


def _rmtguard_coarse_to_fine_run(x, args, seed: int) -> tuple[np.ndarray, dict]:
    """Probe a label-free coarse-to-fine workflow without promoting it to default.

    The coarse layer uses a PC-rule baseline only to define broad compartments.
    RMTGuard is then allowed to split a compartment only when its own guarded
    fit returns an interpretable multi-cluster result.
    """

    coarse_labels, metadata = _coarse_pca_labels(x, args, seed)
    final_labels = np.asarray([f"coarse_{label}.no_fine_call" for label in coarse_labels], dtype=object)
    fine_signal_pcs: list[int] = []
    fine_embedding_pcs: list[int] = []
    fine_ok = 0
    fine_no_call = 0
    fine_skipped = 0

    for coarse_label in sorted(np.unique(coarse_labels)):
        idx = np.flatnonzero(coarse_labels == coarse_label)
        if idx.size < args.coarse_min_cells:
            fine_skipped += 1
            continue
        fine_seed = int(seed + 1009 + int(coarse_label))
        result = _fit_rmtguard(x[idx], args, fine_seed)
        fine_signal_pcs.append(int(result.n_signal_pcs))
        fine_embedding_pcs.append(int(result.n_embedding_pcs))
        fine_cluster_n = int(np.unique(result.cluster_labels).size)
        if result.analysis_status == "ok" and fine_cluster_n >= 2:
            fine_ok += 1
            final_labels[idx] = np.asarray(
                [f"coarse_{coarse_label}.fine_{label}" for label in result.cluster_labels],
                dtype=object,
            )
        else:
            fine_no_call += 1

    metadata.update(
        {
            "coarse_to_fine_rule": "label_free_coarse_pca_then_guarded_within_compartment_rmtguard",
            "coarse_min_cells": int(args.coarse_min_cells),
            "fine_total_compartments": int(np.unique(coarse_labels).size),
            "fine_callable_compartments": int(fine_ok),
            "fine_no_call_compartments": int(fine_no_call),
            "fine_skipped_compartments": int(fine_skipped),
            "fine_mean_signal_pcs": float(np.mean(fine_signal_pcs)) if fine_signal_pcs else "",
            "fine_mean_embedding_pcs": float(np.mean(fine_embedding_pcs)) if fine_embedding_pcs else "",
            "analysis_status": "experimental_probe",
        }
    )
    return final_labels, metadata


def _run_one_method(adata, method: str, args) -> list[dict]:
    rng = np.random.default_rng(args.random_state)
    rows = []
    for run_id in range(args.n_repeats):
        seed = int(args.random_state + run_id)
        n_sample = max(10, int(round(adata.n_obs * args.sample_fraction)))
        selected = np.sort(rng.choice(adata.n_obs, size=n_sample, replace=False))
        x = adata.layers["counts"][selected] if "counts" in adata.layers else adata.X[selected]
        metadata = {}
        if method == "rmtguard":
            labels, metadata = _rmtguard_run(x, args, seed)
        elif method == "rmtguard_strict_signal":
            labels, metadata = _rmtguard_strict_signal_run(x, args, seed)
        elif method == "rmtguard_fixed_k":
            labels, metadata = _rmtguard_fixed_k_run(x, args, seed)
        elif method == "rmtguard_coarse_to_fine":
            labels, metadata = _rmtguard_coarse_to_fine_run(x, args, seed)
        elif method == "fixed_pcs_30":
            labels = _fixed_pca_labels(x, 30, seed)
        elif method == "fixed_pcs_50":
            labels = _fixed_pca_labels(x, 50, seed)
        elif method == "scanpy_default_like":
            labels = _fixed_pca_labels(x, 50, seed)
        elif method in {"elbow_rule", "parallel_analysis", "jackstraw_like"}:
            labels, metadata = _pc_rule_pca_labels(x, method, args, seed)
        else:
            raise ValueError(f"Unknown method: {method}")
        rows.append(
            {
                "run_id": run_id,
                "method": method,
                "seed": seed,
                "cell_indices": selected.tolist(),
                "labels": np.asarray(labels).astype(str).tolist(),
                "n_cells": int(n_sample),
                "cluster_n": int(np.unique(labels).size),
                **metadata,
            }
        )
    return rows


def _pairwise_stability(run_rows: list[dict]) -> float:
    scores = []
    for left, right in combinations(run_rows, 2):
        left_map = {cell: label for cell, label in zip(left["cell_indices"], left["labels"])}
        right_map = {cell: label for cell, label in zip(right["cell_indices"], right["labels"])}
        common = sorted(set(left_map) & set(right_map))
        if len(common) < 5:
            continue
        scores.append(adjusted_rand_score([left_map[i] for i in common], [right_map[i] for i in common]))
    return float(np.mean(scores)) if scores else float("nan")


def _pairwise_records(dataset_id: str, method: str, run_rows: list[dict]) -> list[dict]:
    records = []
    for left, right in combinations(run_rows, 2):
        left_map = {cell: label for cell, label in zip(left["cell_indices"], left["labels"])}
        right_map = {cell: label for cell, label in zip(right["cell_indices"], right["labels"])}
        common = sorted(set(left_map) & set(right_map))
        if len(common) < 5:
            continue
        records.append(
            {
                "dataset_id": dataset_id,
                "method": method,
                "left_run_id": int(left["run_id"]),
                "right_run_id": int(right["run_id"]),
                "pair_key": f"{left['run_id']}__{right['run_id']}",
                "overlap_n": int(len(common)),
                "pairwise_ari": float(
                    adjusted_rand_score(
                        [left_map[i] for i in common],
                        [right_map[i] for i in common],
                    )
                ),
            }
        )
    return records


def _run_dataset(path: Path, dataset_id: str, args) -> tuple[list[dict], list[dict], list[dict]]:
    import anndata as ad

    adata = ad.read_h5ad(path)
    method_rows = []
    summary_rows = []
    pairwise_rows = []
    for method in args.methods:
        runs = _run_one_method(adata, method, args)
        for row in runs:
            method_row = {key: value for key, value in row.items() if key not in {"cell_indices", "labels"}}
            method_rows.append({"dataset_id": dataset_id, **method_row})
        pairwise = _pairwise_records(dataset_id, method, runs)
        pairwise_rows.extend(pairwise)
        summary_rows.append(
            {
                "dataset_id": dataset_id,
                "method": method,
                "n_repeats": args.n_repeats,
                "sample_fraction": args.sample_fraction,
                "mean_pairwise_ari": float(np.mean([row["pairwise_ari"] for row in pairwise])) if pairwise else float("nan"),
                "mean_cluster_n": float(np.mean([r["cluster_n"] for r in runs])),
                "mean_n_cells": float(np.mean([r["n_cells"] for r in runs])),
            }
        )
    return summary_rows, method_rows, pairwise_rows


def _dataset_checkpoint_paths(outdir: Path, dataset_id: str) -> tuple[Path, Path, Path]:
    return (
        outdir / f"{dataset_id}_stability_summary.tsv",
        outdir / f"{dataset_id}_stability_runs.tsv",
        outdir / f"{dataset_id}_stability_pairwise.tsv",
    )


def _load_or_run_dataset(path: Path, dataset_id: str, args) -> tuple[list[dict], list[dict], list[dict]]:
    summary_path, runs_path, pairwise_path = _dataset_checkpoint_paths(args.outdir, dataset_id)
    if (
        not args.force
        and summary_path.exists()
        and runs_path.exists()
        and pairwise_path.exists()
    ):
        return _read_tsv(summary_path), _read_tsv(runs_path), _read_tsv(pairwise_path)
    dataset_summary, dataset_runs, dataset_pairwise = _run_dataset(path, dataset_id, args)
    _write_tsv_atomic(summary_path, dataset_summary)
    _write_tsv_atomic(runs_path, dataset_runs)
    _write_tsv_atomic(pairwise_path, dataset_pairwise)
    return dataset_summary, dataset_runs, dataset_pairwise


def main() -> int:
    parser = argparse.ArgumentParser(description="Run subsampling stability benchmarks on prepared h5ad datasets.")
    parser.add_argument("--processed-dir", type=Path, default=ROOT / "data" / "processed")
    parser.add_argument("--outdir", type=Path, default=ROOT / "results" / "stability_benchmarks")
    parser.add_argument("--datasets", nargs="+", default=["pbmc3k_10x"])
    parser.add_argument("--methods", nargs="+", default=["rmtguard", "scanpy_default_like", "fixed_pcs_30", "fixed_pcs_50"])
    parser.add_argument("--fixed-k", type=int, default=8)
    parser.add_argument("--n-repeats", type=int, default=5)
    parser.add_argument("--sample-fraction", type=float, default=0.8)
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
    parser.add_argument("--low-signal-rescue-rule", default="off", choices=["off", "stable_embedding", "null_calibrated_stable_embedding"])
    parser.add_argument("--low-signal-rescue-max-pcs", type=int, default=12)
    parser.add_argument("--low-signal-rescue-min-pcs", type=int, default=2)
    parser.add_argument("--low-signal-rescue-stability-threshold", type=float, default=0.90)
    parser.add_argument("--low-signal-rescue-null-permutations", type=int, default=10)
    parser.add_argument("--low-signal-rescue-null-quantile", type=float, default=0.95)
    parser.add_argument("--low-signal-rescue-min-eigen-ratio", type=float, default=0.95)
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
    parser.add_argument("--baseline-permutations", type=int, default=20)
    parser.add_argument("--coarse-pc-rule", default="elbow_rule", choices=["elbow_rule", "parallel_analysis"])
    parser.add_argument("--coarse-min-pcs", type=int, default=5)
    parser.add_argument("--coarse-max-pcs", type=int, default=50)
    parser.add_argument("--coarse-max-clusters", type=int, default=8)
    parser.add_argument("--coarse-min-cells", type=int, default=60)
    parser.add_argument("--force", action="store_true", help="Recompute dataset checkpoints even when they already exist.")
    args = parser.parse_args()

    dataset_paths = {
        dataset_id: args.processed_dir / filename
        for dataset_id, filename in DATASET_FILENAMES.items()
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    run_rows = []
    pairwise_rows = []
    for dataset_id in args.datasets:
        if dataset_id not in dataset_paths:
            raise KeyError(f"Unknown dataset '{dataset_id}'. Available: {sorted(dataset_paths)}")
        path = dataset_paths[dataset_id]
        if not path.exists():
            raise FileNotFoundError(f"Prepared dataset not found: {path}")
        dataset_summary, dataset_runs, dataset_pairwise = _load_or_run_dataset(path, dataset_id, args)
        summary_rows.extend(dataset_summary)
        run_rows.extend(dataset_runs)
        pairwise_rows.extend(dataset_pairwise)

    summary_path = args.outdir / "stability_summary.tsv"
    _write_tsv_atomic(summary_path, summary_rows)

    runs_path = args.outdir / "stability_runs.tsv"
    _write_tsv_atomic(runs_path, run_rows)

    pairwise_path = args.outdir / "stability_pairwise.tsv"
    _write_tsv_atomic(pairwise_path, pairwise_rows)

    metadata_path = args.outdir / "stability_metadata.json"
    metadata = vars(args) | {"completed_datasets": list(args.datasets), "dataset_filenames": DATASET_FILENAMES}
    _write_json_atomic(metadata_path, metadata)

    print(summary_path)
    print(runs_path)
    print(pairwise_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

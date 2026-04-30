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
    "kang_ifnb_pbmc": "kang_ifnb_pbmc.h5ad",
    "baron_pancreas": "baron_pancreas.h5ad",
    "pbmc68k_zheng2017": "pbmc68k_zheng2017.h5ad",
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
        "accepted_embedding_pcs": int(embedding_diag.get("accepted_embedding_pcs", result.n_embedding_pcs)),
        "embedding_rule": embedding_diag.get("rule", args.embedding_rule),
        "embedding_source": embedding_diag.get("source", args.embedding_source),
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
        elif method == "fixed_pcs_30":
            labels = _fixed_pca_labels(x, 30, seed)
        elif method == "fixed_pcs_50":
            labels = _fixed_pca_labels(x, 50, seed)
        elif method == "scanpy_default_like":
            labels = _fixed_pca_labels(x, 50, seed)
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


def _run_dataset(path: Path, dataset_id: str, args) -> tuple[list[dict], list[dict]]:
    import anndata as ad

    adata = ad.read_h5ad(path)
    method_rows = []
    summary_rows = []
    for method in args.methods:
        runs = _run_one_method(adata, method, args)
        for row in runs:
            method_row = {key: value for key, value in row.items() if key not in {"cell_indices", "labels"}}
            method_rows.append({"dataset_id": dataset_id, **method_row})
        summary_rows.append(
            {
                "dataset_id": dataset_id,
                "method": method,
                "n_repeats": args.n_repeats,
                "sample_fraction": args.sample_fraction,
                "mean_pairwise_ari": _pairwise_stability(runs),
                "mean_cluster_n": float(np.mean([r["cluster_n"] for r in runs])),
                "mean_n_cells": float(np.mean([r["n_cells"] for r in runs])),
            }
        )
    return summary_rows, method_rows


def _dataset_checkpoint_paths(outdir: Path, dataset_id: str) -> tuple[Path, Path]:
    return (
        outdir / f"{dataset_id}_stability_summary.tsv",
        outdir / f"{dataset_id}_stability_runs.tsv",
    )


def _load_or_run_dataset(path: Path, dataset_id: str, args) -> tuple[list[dict], list[dict]]:
    summary_path, runs_path = _dataset_checkpoint_paths(args.outdir, dataset_id)
    if not args.force and summary_path.exists() and runs_path.exists():
        return _read_tsv(summary_path), _read_tsv(runs_path)
    dataset_summary, dataset_runs = _run_dataset(path, dataset_id, args)
    _write_tsv_atomic(summary_path, dataset_summary)
    _write_tsv_atomic(runs_path, dataset_runs)
    return dataset_summary, dataset_runs


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
    parser.add_argument("--force", action="store_true", help="Recompute dataset checkpoints even when they already exist.")
    args = parser.parse_args()

    dataset_paths = {
        dataset_id: args.processed_dir / filename
        for dataset_id, filename in DATASET_FILENAMES.items()
    }
    args.outdir.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    run_rows = []
    for dataset_id in args.datasets:
        if dataset_id not in dataset_paths:
            raise KeyError(f"Unknown dataset '{dataset_id}'. Available: {sorted(dataset_paths)}")
        path = dataset_paths[dataset_id]
        if not path.exists():
            raise FileNotFoundError(f"Prepared dataset not found: {path}")
        dataset_summary, dataset_runs = _load_or_run_dataset(path, dataset_id, args)
        summary_rows.extend(dataset_summary)
        run_rows.extend(dataset_runs)

    summary_path = args.outdir / "stability_summary.tsv"
    _write_tsv_atomic(summary_path, summary_rows)

    runs_path = args.outdir / "stability_runs.tsv"
    _write_tsv_atomic(runs_path, run_rows)

    metadata_path = args.outdir / "stability_metadata.json"
    metadata = vars(args) | {"completed_datasets": list(args.datasets), "dataset_filenames": DATASET_FILENAMES}
    _write_json_atomic(metadata_path, metadata)

    print(summary_path)
    print(runs_path)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

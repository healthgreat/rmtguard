from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler

from rmtguard import (
    RMTGuard,
    RMTGuardConfig,
    simulate_continuous_trajectory,
    simulate_low_rank_counts,
    simulate_null_counts,
)


def _fixed_pca_kmeans(counts: np.ndarray, labels: np.ndarray, n_pcs: int, random_state: int) -> dict:
    n_clusters = int(np.unique(labels).size)
    if n_clusters < 2:
        return {"method": f"fixed_pcs_{n_pcs}", "ari": float("nan"), "nmi": float("nan")}
    x = np.log1p(counts / np.maximum(counts.sum(axis=1, keepdims=True), 1e-12) * 1e4)
    x = StandardScaler().fit_transform(x)
    pcs = PCA(n_components=min(n_pcs, x.shape[0] - 1, x.shape[1]), random_state=random_state).fit_transform(x)
    pred = KMeans(n_clusters=n_clusters, n_init=20, random_state=random_state).fit_predict(pcs)
    return {
        "method": f"fixed_pcs_{n_pcs}",
        "ari": float(adjusted_rand_score(labels, pred)),
        "nmi": float(normalized_mutual_info_score(labels, pred)),
    }


def _run_rmtguard(name: str, counts: np.ndarray, labels, batches, args) -> dict:
    result = RMTGuard(
        RMTGuardConfig(
            hvg_grid=tuple(args.hvg_grid),
            max_pcs=args.max_pcs,
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
            random_state=args.random_state,
            cluster_grid=tuple(range(2, args.max_clusters + 1)),
        )
    ).fit(counts, batches=batches, benchmark_metadata={"scenario": name})

    labels_arr = np.asarray(labels)
    if np.unique(labels_arr).size > 1:
        ari = float(adjusted_rand_score(labels_arr, result.cluster_labels))
        nmi = float(normalized_mutual_info_score(labels_arr, result.cluster_labels))
    else:
        ari = float("nan")
        nmi = float("nan")
    return {
        "method": "rmtguard",
        "ari": ari,
        "nmi": nmi,
        "selected_hvg_n": result.selected_hvg_n,
        "n_signal_pcs": result.n_signal_pcs,
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
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
        "n_neighbors": result.n_neighbors,
        "cluster_n": result.cluster_n,
        "mp_edge": result.mp_edge,
        "selected_edge": result.pc_diagnostics["selected_edge"],
        "bulk_ks": result.bulk_ks,
        "null_false_positive_rate": result.null_calibration["null_false_positive_rate"],
        "runtime_seconds": result.benchmark_metadata["runtime_seconds"],
        "peak_memory_mb": result.benchmark_metadata["peak_memory_mb"],
    }


def _scenarios(random_state: int, n_cells: int, n_genes: int):
    counts, labels = simulate_null_counts(n_cells=n_cells, n_genes=n_genes, random_state=random_state)
    yield "pure_null", counts, labels, None
    counts, labels, batches = simulate_low_rank_counts(n_cells=n_cells, n_genes=n_genes, random_state=random_state + 1)
    yield "planted_low_rank", counts, labels, batches
    counts, labels, batches = simulate_low_rank_counts(n_cells=n_cells, n_genes=n_genes, rare_fraction=0.04, random_state=random_state + 2)
    yield "rare_state", counts, labels, batches
    counts, labels, batches = simulate_low_rank_counts(n_cells=n_cells, n_genes=n_genes, batch_effect=True, random_state=random_state + 3)
    yield "batch_effect", counts, labels, batches
    counts, labels, batches = simulate_low_rank_counts(n_cells=n_cells, n_genes=n_genes, dropout_rate=0.35, random_state=random_state + 4)
    yield "dropout_stress", counts, labels, batches
    counts, pseudotime = simulate_continuous_trajectory(n_cells=n_cells, n_genes=n_genes, random_state=random_state + 5)
    bins = np.digitize(pseudotime, bins=np.quantile(pseudotime, [0.33, 0.66]))
    yield "continuous_trajectory", counts, bins, None
    counts, labels, batches = simulate_low_rank_counts(
        n_cells=n_cells,
        n_genes=n_genes,
        n_states=4,
        markers_per_state=12,
        dropout_rate=0.25,
        random_state=random_state + 6,
    )
    yield "overclustering_stress", counts, labels, batches


def main() -> int:
    parser = argparse.ArgumentParser(description="Run RMTGuard synthetic stress benchmarks.")
    parser.add_argument("--outdir", type=Path, default=Path("results/synthetic_benchmarks"))
    parser.add_argument("--n-cells", type=int, default=300)
    parser.add_argument("--n-genes", type=int, default=800)
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[200, 400, 800, 1200])
    parser.add_argument("--max-pcs", type=int, default=40)
    parser.add_argument("--max-clusters", type=int, default=10)
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
    parser.add_argument("--random-state", type=int, default=20260427)
    args = parser.parse_args()

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    details = {}
    for name, counts, labels, batches in _scenarios(args.random_state, args.n_cells, args.n_genes):
        rmt_row = {"scenario": name, **_run_rmtguard(name, counts, labels, batches, args)}
        rows.append(rmt_row)
        if np.unique(labels).size > 1:
            for n_pcs in (30, 50):
                rows.append({"scenario": name, **_fixed_pca_kmeans(counts, labels, n_pcs, args.random_state)})
        details[name] = {"n_cells": int(counts.shape[0]), "n_genes": int(counts.shape[1])}

    csv_path = args.outdir / "synthetic_benchmark_summary.csv"
    fieldnames = sorted({key for row in rows for key in row})
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    json_path = args.outdir / "synthetic_benchmark_metadata.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(details, handle, indent=2)
    print(csv_path)
    print(json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

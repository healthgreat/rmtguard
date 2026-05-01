"""Command line entry points for RMTGuard."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from .core import RMTGuard, RMTGuardConfig


def _read_matrix(path: Path) -> np.ndarray:
    suffix = path.suffix.lower()
    if suffix == ".npy":
        return np.load(path)
    if suffix in {".csv", ".txt", ".tsv"}:
        delimiter = "," if suffix == ".csv" else "\t"
        return np.loadtxt(path, delimiter=delimiter)
    raise ValueError(f"Unsupported matrix format: {path}")


def _result_summary(result) -> dict:
    return {
        "selected_hvg_n": result.selected_hvg_n,
        "n_signal_pcs": result.n_signal_pcs,
        "mp_edge": result.mp_edge,
        "noise_variance": result.noise_variance,
        "bulk_ks": result.bulk_ks,
        "n_neighbors": result.n_neighbors,
        "cluster_n": result.cluster_n,
        "n_embedding_pcs": result.n_embedding_pcs,
        "pc_diagnostics": result.pc_diagnostics,
        "hvg_diagnostics": result.hvg_diagnostics,
        "embedding_diagnostics": result.embedding_diagnostics,
        "resolution_scan": result.resolution_scan,
        "null_calibration": result.null_calibration,
        "benchmark_metadata": result.benchmark_metadata,
        "hvg_scan": [asdict(r) for r in result.hvg_scan],
        "neighbor_scan": [asdict(r) for r in result.neighbor_scan],
        "cluster_scan": [asdict(r) for r in result.cluster_scan],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RMTGuard on a dense expression matrix.")
    parser.add_argument("matrix", type=Path, help="Cell-by-gene matrix in .npy, .csv, .tsv, or .txt format.")
    parser.add_argument("--already-log-normalized", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("results/rmtguard_summary.json"))
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--max-pcs", type=int, default=80)
    parser.add_argument("--min-embedding-pcs", type=int, default=0)
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
    args = parser.parse_args(argv)

    matrix = _read_matrix(args.matrix)
    config = RMTGuardConfig(
        hvg_grid=tuple(args.hvg_grid),
        max_pcs=args.max_pcs,
        min_embedding_pcs=args.min_embedding_pcs,
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
        low_signal_rescue_null_permutations=args.low_signal_rescue_null_permutations,
        low_signal_rescue_null_quantile=args.low_signal_rescue_null_quantile,
        low_signal_rescue_min_eigen_ratio=args.low_signal_rescue_min_eigen_ratio,
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
    )
    result = RMTGuard(config).fit(matrix, already_log_normalized=args.already_log_normalized)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as handle:
        json.dump(_result_summary(result), handle, indent=2)
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

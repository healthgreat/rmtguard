from __future__ import annotations

"""Profile one RMTGuard fit step by step on a prepared h5ad file."""

import argparse
import time
from pathlib import Path

import numpy as np

from rmtguard import RMTGuardConfig
from rmtguard.cluster import choose_graph_modularity_clusters, choose_n_neighbors
from rmtguard.core import RMTGuard
from rmtguard.preprocess import normalize_total_log1p, to_dense_array
from rmtguard.rmt import spectrum_from_matrix


ROOT = Path(__file__).resolve().parents[1]


def log_step(label: str, start: float) -> float:
    now = time.perf_counter()
    print(f"{label}\t{now - start:.3f}s", flush=True)
    return now


def main() -> int:
    parser = argparse.ArgumentParser(description="Profile RMTGuard fit internals.")
    parser.add_argument("--h5ad", type=Path, default=ROOT / "data" / "processed" / "pbmc3k_10x.h5ad")
    parser.add_argument("--sample-fraction", type=float, default=0.8)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument("--whiten", default="biwhiten", choices=["biwhiten", "zscore"])
    parser.add_argument("--embedding-stability-repeats", type=int, default=5)
    args = parser.parse_args()

    import anndata as ad

    t = time.perf_counter()
    adata = ad.read_h5ad(args.h5ad)
    t = log_step("read_h5ad", t)

    rng = np.random.default_rng(args.random_state)
    n_sample = max(10, int(round(adata.n_obs * args.sample_fraction)))
    selected = np.sort(rng.choice(adata.n_obs, size=n_sample, replace=False))
    x = adata.layers["counts"][selected] if "counts" in adata.layers else adata.X[selected]
    t = log_step("slice_matrix", t)

    cfg = RMTGuardConfig(
        hvg_grid=(500, 1000, 2000),
        max_pcs=50,
        whiten=args.whiten,
        embedding_stability_repeats=args.embedding_stability_repeats,
        random_state=args.random_state,
    )
    guard = RMTGuard(cfg)

    counts_or_log = to_dense_array(x)
    t = log_step(f"to_dense {counts_or_log.shape}", t)

    x_log = normalize_total_log1p(counts_or_log, target_sum=cfg.target_sum)
    t = log_step("normalize_total_log1p", t)

    hvg_scan, selected_hvg_n = guard._scan_hvgs(x_log)
    print(f"selected_hvg_n\t{selected_hvg_n}", flush=True)
    t = log_step("scan_hvgs", t)

    hvg_indices = guard._select_hvg_indices(x_log, selected_hvg_n)
    t = log_step("select_hvg_indices", t)

    x_guarded = guard._prepare_hvg_matrix(x_log[:, hvg_indices])
    t = log_step("prepare_hvg_matrix", t)

    spectrum = spectrum_from_matrix(x_guarded)
    t = log_step("rmt_spectrum", t)

    pc_decision = guard._classify_spectrum(spectrum, x_guarded, use_permutation=True)
    print(f"n_signal_pcs\t{pc_decision['n_signal_pcs']}", flush=True)
    t = log_step("classify_spectrum", t)

    x_embedding = guard._prepare_embedding_matrix(x_log[:, hvg_indices])
    t = log_step("prepare_embedding_matrix", t)

    embedding_spectrum = spectrum_from_matrix(x_embedding)
    t = log_step("embedding_spectrum", t)

    embedding, noise_embedding, embedding_diagnostics = guard._make_embeddings(
        spectrum,
        embedding_spectrum,
        pc_decision,
        x_embedding,
    )
    print(
        "embedding_pcs\t"
        + str(embedding.shape[1])
        + "\tnear_edge_candidates\t"
        + str(embedding_diagnostics.get("near_edge_candidate_pcs")),
        flush=True,
    )
    t = log_step("make_embeddings", t)

    n_neighbors, _neighbor_scan = choose_n_neighbors(embedding, noise_embedding, grid=cfg.n_neighbors_grid)
    print(f"n_neighbors\t{n_neighbors}", flush=True)
    t = log_step("choose_n_neighbors", t)

    labels, _resolution_scan = choose_graph_modularity_clusters(
        embedding,
        noise_embedding,
        n_neighbors=n_neighbors,
        resolution_grid=(1.0,),
        stability_threshold=0.8,
        min_cluster_fraction=cfg.min_cluster_fraction,
    )
    print(f"cluster_n\t{np.unique(labels).size}", flush=True)
    log_step("graph_modularity", t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

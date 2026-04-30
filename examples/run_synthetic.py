from __future__ import annotations

from pathlib import Path

import numpy as np

from rmtguard import RMTGuard, RMTGuardConfig, simulate_low_rank_counts


def simulate_counts(
    n_cells: int = 600,
    n_genes: int = 1200,
    n_clusters: int = 4,
    markers_per_cluster: int = 35,
    random_state: int = 7,
) -> tuple[np.ndarray, np.ndarray]:
    counts, labels, _ = simulate_low_rank_counts(
        n_cells=n_cells,
        n_genes=n_genes,
        n_states=n_clusters,
        markers_per_state=markers_per_cluster,
        random_state=random_state,
    )
    return counts, labels


def main() -> None:
    counts, labels = simulate_counts()
    config = RMTGuardConfig(
        hvg_grid=(200, 400, 800, 1000),
        max_pcs=40,
        pc_rule="mp_tw",
        n_neighbors_grid=(10, 15, 20, 30, 50),
        cluster_grid=tuple(range(2, 10)),
        random_state=11,
    )
    result = RMTGuard(config).fit(counts)

    print("RMTGuard synthetic demo")
    print(f"selected_hvg_n: {result.selected_hvg_n}")
    print(f"n_signal_pcs: {result.n_signal_pcs}")
    print(f"mp_edge: {result.mp_edge:.4f}")
    print(f"bulk_ks: {result.bulk_ks:.4f}")
    print(f"n_neighbors: {result.n_neighbors}")
    print(f"fallback_cluster_n: {result.cluster_n}")
    print(f"true_cluster_n: {len(np.unique(labels))}")
    print(f"runtime_seconds: {result.benchmark_metadata['runtime_seconds']:.3f}")
    print(f"peak_memory_mb: {result.benchmark_metadata['peak_memory_mb']:.2f}")

    out_dir = Path(__file__).resolve().parents[1] / "results"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "synthetic_rmtguard_summary.csv"
    with out_file.open("w", encoding="utf-8") as handle:
        handle.write("section,parameter,value\n")
        handle.write(f"selected,selected_hvg_n,{result.selected_hvg_n}\n")
        handle.write(f"selected,n_signal_pcs,{result.n_signal_pcs}\n")
        handle.write(f"selected,mp_edge,{result.mp_edge:.8g}\n")
        handle.write(f"selected,bulk_ks,{result.bulk_ks:.8g}\n")
        handle.write(f"selected,n_neighbors,{result.n_neighbors}\n")
        handle.write(f"selected,fallback_cluster_n,{result.cluster_n}\n")
        handle.write(f"diagnostics,pc_rule,{result.pc_diagnostics['rule']}\n")
        handle.write(f"diagnostics,selected_edge,{result.pc_diagnostics['selected_edge']:.8g}\n")
        handle.write(f"diagnostics,tw_edge,{result.pc_diagnostics['tw_edge']:.8g}\n")
        handle.write(f"diagnostics,null_false_positive_rate,{result.null_calibration['null_false_positive_rate']}\n")
        handle.write(f"diagnostics,runtime_seconds,{result.benchmark_metadata['runtime_seconds']:.8g}\n")
        handle.write(f"diagnostics,peak_memory_mb,{result.benchmark_metadata['peak_memory_mb']:.8g}\n")
        for record in result.hvg_scan:
            handle.write(f"hvg_scan,n_hvg,{record.n_hvg}\n")
            handle.write(f"hvg_scan_{record.n_hvg},n_signal_pcs,{record.n_signal_pcs}\n")
            handle.write(f"hvg_scan_{record.n_hvg},bulk_ks,{record.bulk_ks:.8g}\n")
            handle.write(f"hvg_scan_{record.n_hvg},selected,{record.selected}\n")
        for record in result.neighbor_scan:
            handle.write(f"neighbor_scan_{record.n_neighbors},median_jaccard,{record.median_jaccard:.8g}\n")
            handle.write(f"neighbor_scan_{record.n_neighbors},selected,{record.selected}\n")
        for record in result.cluster_scan:
            handle.write(f"cluster_scan_{record.n_clusters},stability_ari,{record.stability_ari:.8g}\n")
            handle.write(f"cluster_scan_{record.n_clusters},min_cluster_fraction,{record.min_cluster_fraction:.8g}\n")
            handle.write(f"cluster_scan_{record.n_clusters},silhouette,{record.silhouette:.8g}\n")
            handle.write(f"cluster_scan_{record.n_clusters},selected,{record.selected}\n")
    print(f"summary_csv: {out_file}")


if __name__ == "__main__":
    main()

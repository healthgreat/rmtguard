"""Optional Scanpy integration for RMTGuard."""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
from sklearn.metrics import adjusted_rand_score

from .cluster import standardize_embedding
from .core import RMTGuard, RMTGuardConfig, RMTGuardResult


def fit_anndata(
    adata,
    config: RMTGuardConfig | None = None,
    layer: str | None = None,
    already_log_normalized: bool = False,
    key: str = "rmtguard",
) -> RMTGuardResult:
    """Fit RMTGuard on AnnData and store embedding/diagnostics."""

    cfg = config or RMTGuardConfig()
    matrix = adata.layers[layer] if layer is not None else adata.X
    batches = adata.obs[cfg.batch_key].to_numpy() if cfg.batch_key is not None else None
    result = RMTGuard(cfg).fit(
        matrix,
        already_log_normalized=already_log_normalized,
        batches=batches,
        benchmark_metadata={"anndata_layer": layer or "X", "batch_key": cfg.batch_key},
    )

    hvg_mask = np.zeros(adata.n_vars, dtype=bool)
    hvg_mask[result.hvg_indices] = True
    adata.var[f"{key}_hvg"] = hvg_mask
    adata.obsm[f"X_{key}"] = result.embedding
    adata.obs[f"{key}_leiden"] = result.cluster_labels.astype(str)
    adata.uns[key] = {
        "selected_hvg_n": result.selected_hvg_n,
        "n_signal_pcs": result.n_signal_pcs,
        "mp_edge": result.mp_edge,
        "noise_variance": result.noise_variance,
        "bulk_ks": result.bulk_ks,
        "n_neighbors": result.n_neighbors,
        "cluster_n_fallback": result.cluster_n,
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
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
    if cfg.resolution_rule == "leiden_stability":
        try:
            select_leiden_resolution(
                adata,
                result,
                resolutions=cfg.leiden_resolution_grid,
                key=key,
                stability_threshold=cfg.cluster_stability_threshold,
                min_cluster_fraction=cfg.min_cluster_fraction,
            )
        except Exception as exc:  # Scanpy may lack leidenalg in lightweight installs.
            adata.uns[key]["leiden_warning"] = str(exc)
    return result


def select_leiden_resolution(
    adata,
    result: RMTGuardResult,
    resolutions: tuple[float, ...] = (0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0),
    key: str = "rmtguard",
    stability_threshold: float = 0.85,
    min_cluster_fraction: float = 0.02,
) -> float | None:
    """Select the largest Leiden resolution stable to adding RMT-null PCs.

    Requires scanpy plus a Leiden backend such as leidenalg. If those packages
    are unavailable, an ImportError is raised with the root cause.
    """

    try:
        import scanpy as sc
    except ImportError as exc:
        raise ImportError("scanpy is required for select_leiden_resolution") from exc

    if result.embedding.shape[1] == 0:
        return None

    n_neighbors = result.n_neighbors or min(15, max(2, adata.n_obs - 1))
    z_signal = standardize_embedding(result.embedding)
    if result.noise_embedding.size > 0:
        z_aug = np.column_stack([z_signal, standardize_embedding(result.noise_embedding)])
    else:
        z_aug = z_signal

    adata.obsm[f"X_{key}_signal"] = z_signal
    adata.obsm[f"X_{key}_augmented"] = z_aug
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=f"X_{key}_signal", key_added=f"{key}_signal")
    sc.pp.neighbors(adata, n_neighbors=n_neighbors, use_rep=f"X_{key}_augmented", key_added=f"{key}_augmented")

    records = []
    selected = None
    for resolution in resolutions:
        signal_key = f"{key}_leiden_signal_{resolution}"
        aug_key = f"{key}_leiden_aug_{resolution}"
        sc.tl.leiden(
            adata,
            resolution=float(resolution),
            neighbors_key=f"{key}_signal",
            key_added=signal_key,
        )
        sc.tl.leiden(
            adata,
            resolution=float(resolution),
            neighbors_key=f"{key}_augmented",
            key_added=aug_key,
        )
        signal_labels = adata.obs[signal_key].astype(str).to_numpy()
        aug_labels = adata.obs[aug_key].astype(str).to_numpy()
        ari = float(adjusted_rand_score(signal_labels, aug_labels))
        _, counts = np.unique(signal_labels, return_counts=True)
        min_frac = float(np.min(counts) / adata.n_obs)
        keep = ari >= stability_threshold and min_frac >= min_cluster_fraction
        records.append(
            {
                "resolution": float(resolution),
                "stability_ari": ari,
                "min_cluster_fraction": min_frac,
                "selected": False,
            }
        )
        if keep:
            selected = float(resolution)

    if selected is not None:
        for record in records:
            record["selected"] = record["resolution"] == selected
        sc.tl.leiden(
            adata,
            resolution=selected,
            neighbors_key=f"{key}_signal",
            key_added=f"{key}_leiden",
        )

    adata.uns.setdefault(key, {})
    adata.uns[key]["leiden_resolution_scan"] = records
    adata.uns[key]["selected_leiden_resolution"] = selected
    return selected

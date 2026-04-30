"""Preprocessing utilities for RMTGuard."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import sparse


@dataclass(frozen=True)
class BiwhitenResult:
    x: np.ndarray
    row_scale: np.ndarray
    col_scale: np.ndarray
    n_iter: int
    converged: bool


def to_dense_array(x) -> np.ndarray:
    """Convert numpy/scipy/anndata-like matrices to a dense float array."""

    if sparse.issparse(x):
        x = x.toarray()
    arr = np.asarray(x, dtype=float)
    if arr.ndim != 2:
        raise ValueError("expression matrix must be 2D")
    if np.any(arr < 0):
        raise ValueError("expression matrix contains negative values; pass log data with already_log_normalized=True only if appropriate")
    return arr


def normalize_total_log1p(x: np.ndarray, target_sum: float = 1e4) -> np.ndarray:
    """Library-size normalize counts and apply log1p."""

    x = np.asarray(x, dtype=float)
    totals = np.sum(x, axis=1, keepdims=True)
    totals = np.maximum(totals, np.finfo(float).eps)
    return np.log1p(x / totals * target_sum)


def dispersion_scores(x: np.ndarray) -> np.ndarray:
    """Return raw variance-to-mean dispersion scores on log data."""

    means = np.mean(x, axis=0)
    variances = np.var(x, axis=0, ddof=1)
    dispersion = variances / np.maximum(means, 1e-8)
    dispersion[~np.isfinite(dispersion)] = -np.inf
    return dispersion


def normalized_dispersion_scores(x: np.ndarray, n_bins: int = 20) -> np.ndarray:
    """Return mean-binned normalized dispersion scores.

    This follows the practical idea behind Seurat/Scanpy dispersion HVG
    selection: genes are compared against genes with similar average expression
    before ranking by variability.
    """

    means = np.mean(x, axis=0)
    raw = dispersion_scores(x)
    valid = np.isfinite(raw) & np.isfinite(means) & (means > 0)
    scores = np.full(x.shape[1], -np.inf, dtype=float)
    if np.sum(valid) < 2:
        return raw

    log_means = np.log1p(means[valid])
    raw_valid = raw[valid]
    order = np.argsort(log_means)
    bins = np.array_split(order, min(max(1, int(n_bins)), order.size))
    normalized = np.zeros_like(raw_valid, dtype=float)
    for bin_indices in bins:
        values = raw_valid[bin_indices]
        center = np.mean(values)
        scale = np.std(values, ddof=1) if values.size > 1 else 0.0
        if not np.isfinite(scale) or scale <= np.finfo(float).eps:
            normalized[bin_indices] = values - center
        else:
            normalized[bin_indices] = (values - center) / scale
    scores[np.flatnonzero(valid)] = normalized
    return scores


def select_hvg_by_dispersion(x: np.ndarray, n_top: int, method: str = "raw_dispersion") -> np.ndarray:
    """Select HVGs using raw or mean-binned normalized dispersion."""

    if n_top <= 0:
        raise ValueError("n_top must be positive")
    n_top = min(int(n_top), x.shape[1])
    if method == "raw_dispersion":
        dispersion = dispersion_scores(x)
    elif method == "normalized_dispersion":
        dispersion = normalized_dispersion_scores(x)
    else:
        raise ValueError("method must be one of: raw_dispersion, normalized_dispersion")
    order = np.argsort(dispersion)[::-1]
    return np.sort(order[:n_top])


def standardize_genes(x: np.ndarray) -> np.ndarray:
    """Column-center and z-score genes."""

    centered = x - np.mean(x, axis=0, keepdims=True)
    scale = np.std(centered, axis=0, ddof=1, keepdims=True)
    scale = np.maximum(scale, np.finfo(float).eps)
    return centered / scale


def residualize_batches(x: np.ndarray, batches) -> np.ndarray:
    """Remove per-batch gene mean shifts while preserving global gene means."""

    if batches is None:
        return np.asarray(x, dtype=float)
    arr = np.asarray(x, dtype=float)
    labels = np.asarray(batches)
    if labels.shape[0] != arr.shape[0]:
        raise ValueError("batch labels must have one entry per cell")

    global_mean = np.mean(arr, axis=0, keepdims=True)
    adjusted = arr.copy()
    for batch in np.unique(labels):
        mask = labels == batch
        if np.any(mask):
            batch_mean = np.mean(arr[mask], axis=0, keepdims=True)
            adjusted[mask] = arr[mask] - batch_mean + global_mean
    adjusted = np.maximum(adjusted, 0.0)
    return adjusted


def biwhiten(
    x: np.ndarray,
    max_iter: int = 100,
    tol: float = 1e-4,
    factor_clip: tuple[float, float] = (0.2, 5.0),
) -> BiwhitenResult:
    """Alternating row/column variance scaling inspired by Sinkhorn-Knopp.

    The implementation is intentionally conservative: it targets row-wise and
    column-wise mean squares near one, then centers and globally rescales the
    result. It is a practical whitening step for the RMTGuard prototype, not a
    line-for-line reproduction of the sparse PCA paper's algorithm.
    """

    x = np.asarray(x, dtype=float)
    centered = x - np.mean(x, axis=0, keepdims=True)
    x2 = centered**2
    n_cells, n_genes = centered.shape
    row_scale = np.ones(n_cells, dtype=float)
    col_scale = np.ones(n_genes, dtype=float)
    converged = False

    lo, hi = factor_clip
    eps = np.finfo(float).eps
    for iteration in range(1, max_iter + 1):
        old_row = row_scale.copy()
        old_col = col_scale.copy()

        row_var = row_scale**2 * (x2 @ (col_scale**2)) / max(n_genes, 1)
        row_factor = 1.0 / np.sqrt(np.maximum(row_var, eps))
        row_scale *= np.clip(row_factor, lo, hi)

        col_var = col_scale**2 * ((row_scale**2) @ x2) / max(n_cells, 1)
        col_factor = 1.0 / np.sqrt(np.maximum(col_var, eps))
        col_scale *= np.clip(col_factor, lo, hi)

        # Remove the arbitrary global scaling degree of freedom.
        row_gm = np.exp(np.mean(np.log(np.maximum(row_scale, eps))))
        row_scale /= row_gm
        col_scale *= row_gm

        row_delta = np.max(np.abs(np.log(np.maximum(row_scale, eps) / np.maximum(old_row, eps))))
        col_delta = np.max(np.abs(np.log(np.maximum(col_scale, eps) / np.maximum(old_col, eps))))
        if max(row_delta, col_delta) < tol:
            converged = True
            break

    whitened = centered * row_scale[:, None] * col_scale[None, :]
    whitened = whitened - np.mean(whitened, axis=0, keepdims=True)
    global_sd = np.sqrt(np.mean(whitened**2))
    if np.isfinite(global_sd) and global_sd > eps:
        whitened = whitened / global_sd

    return BiwhitenResult(
        x=whitened,
        row_scale=row_scale,
        col_scale=col_scale,
        n_iter=iteration,
        converged=converged,
    )

"""Random matrix helpers used by RMTGuard."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.linalg import svd
from scipy.stats import norm


@dataclass(frozen=True)
class Spectrum:
    """Eigen-spectrum summary for a cell-by-gene matrix."""

    eigenvalues: np.ndarray
    singular_values: np.ndarray
    left_vectors: np.ndarray
    aspect: float


def mp_edges(aspect: float, sigma2: float = 1.0) -> tuple[float, float]:
    """Return Marchenko-Pastur lower and upper edges."""

    if aspect <= 0:
        raise ValueError("aspect must be positive")
    root = np.sqrt(aspect)
    lower = sigma2 * (1.0 - root) ** 2
    upper = sigma2 * (1.0 + root) ** 2
    return float(lower), float(upper)


def mp_pdf(x: np.ndarray, aspect: float, sigma2: float = 1.0) -> np.ndarray:
    """Continuous MP density, conditional on non-zero eigenvalues."""

    x = np.asarray(x, dtype=float)
    lower, upper = mp_edges(aspect, sigma2=sigma2)
    density = np.zeros_like(x, dtype=float)
    mask = (x > lower) & (x < upper)
    if not np.any(mask):
        return density

    z = x[mask] / sigma2
    a, b = mp_edges(aspect, sigma2=1.0)
    numerator = np.sqrt(np.maximum((b - z) * (z - a), 0.0))
    denom = 2.0 * np.pi * aspect * np.maximum(z, np.finfo(float).tiny)
    density[mask] = numerator / denom / sigma2

    # For p > n, the p-by-p covariance has an atom at zero. RMTGuard works with
    # non-zero singular values, so the continuous density is renormalized.
    if aspect > 1.0:
        density *= aspect
    return density


@lru_cache(maxsize=512)
def _mp_grid(aspect_rounded: float, sigma2_rounded: float) -> tuple[np.ndarray, np.ndarray]:
    aspect = float(aspect_rounded)
    sigma2 = float(sigma2_rounded)
    lower, upper = mp_edges(aspect, sigma2=sigma2)
    left = max(lower, np.finfo(float).eps * max(1.0, upper))
    grid = np.linspace(left, upper, 20000)
    pdf = mp_pdf(grid, aspect, sigma2=sigma2)
    cdf = np.zeros_like(grid)
    increments = 0.5 * (pdf[1:] + pdf[:-1]) * np.diff(grid)
    cdf[1:] = np.cumsum(increments)
    if cdf[-1] > 0:
        cdf /= cdf[-1]
    return grid, cdf


def mp_cdf(x: np.ndarray, aspect: float, sigma2: float = 1.0) -> np.ndarray:
    """Numerical MP CDF for the continuous, non-zero part."""

    x = np.asarray(x, dtype=float)
    grid, cdf = _mp_grid(round(float(aspect), 8), round(float(sigma2), 8))
    return np.interp(x, grid, cdf, left=0.0, right=1.0)


def mp_median(aspect: float, sigma2: float = 1.0) -> float:
    """Numerical median of the continuous MP distribution."""

    grid, cdf = _mp_grid(round(float(aspect), 8), round(float(sigma2), 8))
    return float(np.interp(0.5, cdf, grid))


def spectrum_from_matrix(x: np.ndarray) -> Spectrum:
    """Compute covariance eigenvalues using an economy SVD."""

    if x.ndim != 2:
        raise ValueError("x must be a 2D cell-by-gene matrix")
    n_cells, n_genes = x.shape
    if n_cells < 3 or n_genes < 2:
        raise ValueError("x must contain at least 3 cells and 2 genes")

    centered = x - np.mean(x, axis=0, keepdims=True)
    if n_cells <= n_genes:
        gram = centered @ centered.T
        gram /= max(n_cells - 1, 1)
        eigenvalues, left_vectors = np.linalg.eigh(gram)
        order = np.argsort(eigenvalues)[::-1]
        eigenvalues = np.maximum(eigenvalues[order], 0.0)
        left_vectors = left_vectors[:, order]
        singular_values = np.sqrt(eigenvalues * max(n_cells - 1, 1))
    else:
        left_vectors, singular_values, _ = svd(
            centered,
            full_matrices=False,
            check_finite=False,
            lapack_driver="gesdd",
        )
        eigenvalues = (singular_values**2) / max(n_cells - 1, 1)
    aspect = n_genes / max(n_cells - 1, 1)
    return Spectrum(
        eigenvalues=np.asarray(eigenvalues, dtype=float),
        singular_values=np.asarray(singular_values, dtype=float),
        left_vectors=np.asarray(left_vectors, dtype=float),
        aspect=float(aspect),
    )


def estimate_noise_variance(eigenvalues: np.ndarray, aspect: float) -> float:
    """Estimate MP noise variance from the median non-zero eigenvalue."""

    vals = np.asarray(eigenvalues, dtype=float)
    vals = vals[np.isfinite(vals) & (vals > np.finfo(float).eps)]
    if vals.size == 0:
        return 1.0
    observed = float(np.median(vals))
    theoretical = mp_median(aspect, sigma2=1.0)
    if theoretical <= 0 or not np.isfinite(theoretical):
        return 1.0
    sigma2 = observed / theoretical
    return float(max(sigma2, np.finfo(float).eps))


def signal_mask_from_mp(
    eigenvalues: np.ndarray,
    aspect: float,
    edge_buffer: float = 1.02,
) -> tuple[np.ndarray, float, float]:
    """Classify covariance eigenvalues above the MP upper edge as signal."""

    sigma2 = estimate_noise_variance(eigenvalues, aspect)
    _, upper = mp_edges(aspect, sigma2=sigma2)
    edge = upper * edge_buffer
    mask = np.asarray(eigenvalues, dtype=float) > edge
    return mask, float(edge), float(sigma2)


def tracy_widom_edge_proxy(
    n_cells: int,
    n_genes: int,
    sigma2: float,
    alpha: float = 0.01,
    edge_buffer: float = 1.0,
) -> float:
    """Finite-sample upper edge proxy for the largest noise eigenvalue.

    This uses the Johnstone centering/scaling for white Wishart matrices and a
    conservative normal upper quantile as a portable proxy for the Tracy-Widom
    upper tail. It is intentionally paired with optional permutation
    calibration for manuscript-grade analyses.
    """

    n_eff = max(int(n_cells) - 1, 2)
    p_eff = max(int(n_genes), 2)
    alpha = min(max(float(alpha), 1e-6), 0.2)
    root_n = np.sqrt(n_eff)
    root_p = np.sqrt(p_eff)
    mu = sigma2 * ((root_n + root_p) ** 2) / n_eff
    scale = sigma2 * (root_n + root_p) * ((1.0 / root_n) + (1.0 / root_p)) ** (1.0 / 3.0) / n_eff
    z = norm.ppf(1.0 - alpha)
    return float((mu + z * scale) * edge_buffer)


def permutation_max_edges(
    x: np.ndarray,
    n_permutations: int,
    random_state: int = 0,
) -> np.ndarray:
    """Return largest eigenvalue from gene-wise permuted null matrices."""

    if n_permutations <= 0:
        return np.empty(0, dtype=float)
    arr = np.asarray(x, dtype=float)
    rng = np.random.default_rng(random_state)
    out = np.empty(int(n_permutations), dtype=float)
    for i in range(int(n_permutations)):
        permuted = arr.copy()
        for j in range(permuted.shape[1]):
            rng.shuffle(permuted[:, j])
        out[i] = float(spectrum_from_matrix(permuted).eigenvalues[0])
    return out


def bulk_ks_distance(eigenvalues: np.ndarray, aspect: float, sigma2: float, edge: float) -> float:
    """KS distance between observed bulk eigenvalues and the MP null."""

    vals = np.asarray(eigenvalues, dtype=float)
    vals = vals[np.isfinite(vals) & (vals > np.finfo(float).eps) & (vals <= edge)]
    if vals.size < 5:
        return float("nan")

    vals = np.sort(vals)
    observed_cdf = np.arange(1, vals.size + 1, dtype=float) / vals.size
    theoretical_cdf = mp_cdf(vals, aspect=aspect, sigma2=sigma2)
    return float(np.max(np.abs(observed_cdf - theoretical_cdf)))


def effective_feature_count(loadings: np.ndarray) -> np.ndarray:
    """Return inverse participation ratio based effective feature counts."""

    v = np.asarray(loadings, dtype=float)
    if v.ndim == 1:
        v = v.reshape(1, -1)
    denom = np.sum(v**4, axis=1)
    denom = np.maximum(denom, np.finfo(float).eps)
    return 1.0 / denom

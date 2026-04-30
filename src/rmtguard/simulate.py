"""Synthetic stress-test generators for RMTGuard benchmarks."""

from __future__ import annotations

import numpy as np


def simulate_null_counts(
    n_cells: int = 300,
    n_genes: int = 800,
    random_state: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """Pure count noise with library-size variation and no cell states."""

    rng = np.random.default_rng(random_state)
    gene_means = rng.gamma(shape=1.4, scale=1.2, size=n_genes) + 0.02
    size_factors = rng.lognormal(mean=0.0, sigma=0.35, size=n_cells)
    counts = rng.poisson(size_factors[:, None] * gene_means[None, :]).astype(float)
    return counts, np.zeros(n_cells, dtype=int)


def simulate_low_rank_counts(
    n_cells: int = 300,
    n_genes: int = 800,
    n_states: int = 3,
    markers_per_state: int = 30,
    rare_fraction: float | None = None,
    batch_effect: bool = False,
    dropout_rate: float = 0.10,
    random_state: int = 1,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """Counts with planted cell states, optional rare state and batch shift."""

    rng = np.random.default_rng(random_state)
    if rare_fraction is None:
        labels = np.repeat(np.arange(n_states), n_cells // n_states)
        if labels.size < n_cells:
            labels = np.concatenate([labels, rng.integers(0, n_states, size=n_cells - labels.size)])
    else:
        rare_n = max(3, int(round(n_cells * rare_fraction)))
        common = rng.integers(0, max(n_states - 1, 1), size=n_cells - rare_n)
        labels = np.concatenate([common, np.full(rare_n, n_states - 1, dtype=int)])
    rng.shuffle(labels)

    gene_means = rng.gamma(shape=1.5, scale=1.4, size=n_genes) + 0.03
    effects = np.ones((n_states, n_genes), dtype=float)
    for state in range(n_states):
        start = state * markers_per_state
        stop = min(start + markers_per_state, n_genes)
        effects[state, start:stop] = rng.uniform(3.0, 7.0, size=stop - start)

    batches = None
    batch_multiplier = np.ones((n_cells, n_genes), dtype=float)
    if batch_effect:
        batches = rng.integers(0, 2, size=n_cells)
        affected = np.arange(min(80, n_genes))
        batch_multiplier[batches == 1][:, affected] = 1.0
        batch_multiplier[np.ix_(batches == 1, affected)] = rng.uniform(1.8, 2.8, size=affected.size)

    size_factors = rng.lognormal(mean=0.0, sigma=0.35, size=n_cells)
    rates = size_factors[:, None] * gene_means[None, :] * effects[labels] * batch_multiplier
    counts = rng.poisson(rates).astype(float)
    if dropout_rate > 0:
        dropout = rng.random(counts.shape) < np.exp(-rates / 2.0) * dropout_rate
        counts[dropout] = 0.0
    return counts, labels.astype(int), batches


def simulate_continuous_trajectory(
    n_cells: int = 300,
    n_genes: int = 800,
    n_program_genes: int = 80,
    random_state: int = 2,
) -> tuple[np.ndarray, np.ndarray]:
    """Smooth one-dimensional trajectory embedded in count data."""

    rng = np.random.default_rng(random_state)
    pseudotime = np.linspace(0.0, 1.0, n_cells)
    rng.shuffle(pseudotime)
    gene_means = rng.gamma(shape=1.5, scale=1.3, size=n_genes) + 0.03
    program = np.ones((n_cells, n_genes), dtype=float)
    program[:, :n_program_genes] += 4.0 * pseudotime[:, None]
    size_factors = rng.lognormal(mean=0.0, sigma=0.35, size=n_cells)
    counts = rng.poisson(size_factors[:, None] * gene_means[None, :] * program).astype(float)
    return counts, pseudotime

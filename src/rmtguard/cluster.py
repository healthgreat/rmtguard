"""Guarded neighborhood and clustering heuristics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import AgglomerativeClustering, KMeans, SpectralClustering
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.neighbors import NearestNeighbors, kneighbors_graph


@dataclass(frozen=True)
class NeighborRecord:
    n_neighbors: int
    median_jaccard: float
    selected: bool = False


@dataclass(frozen=True)
class ClusterRecord:
    n_clusters: int
    stability_ari: float
    min_cluster_fraction: float
    silhouette: float
    selected: bool = False


def standardize_embedding(z: np.ndarray) -> np.ndarray:
    """Center and scale embedding columns."""

    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("embedding must be 2D")
    if z.shape[1] == 0:
        return z.copy()
    centered = z - np.mean(z, axis=0, keepdims=True)
    scale = np.std(centered, axis=0, ddof=1, keepdims=True)
    scale = np.maximum(scale, np.finfo(float).eps)
    return centered / scale


def _neighbor_sets(z: np.ndarray, n_neighbors: int) -> list[set[int]]:
    n = z.shape[0]
    query_k = min(n_neighbors + 1, n)
    nn = NearestNeighbors(n_neighbors=query_k)
    nn.fit(z)
    indices = nn.kneighbors(z, return_distance=False)
    out: list[set[int]] = []
    for row_id, row in enumerate(indices):
        filtered = [int(i) for i in row if int(i) != row_id][:n_neighbors]
        out.append(set(filtered))
    return out


def median_neighbor_jaccard(z_signal: np.ndarray, z_augmented: np.ndarray, n_neighbors: int) -> float:
    """Median Jaccard overlap of kNN sets before and after adding noise PCs."""

    signal_sets = _neighbor_sets(z_signal, n_neighbors)
    augmented_sets = _neighbor_sets(z_augmented, n_neighbors)
    scores = []
    for left, right in zip(signal_sets, augmented_sets):
        union = left | right
        if not union:
            scores.append(1.0)
        else:
            scores.append(len(left & right) / len(union))
    return float(np.median(scores))


def choose_n_neighbors(
    z_signal: np.ndarray,
    z_noise: np.ndarray | None = None,
    grid: tuple[int, ...] = (10, 15, 20, 30, 50),
    threshold: float = 0.70,
) -> tuple[int | None, list[NeighborRecord]]:
    """Choose the smallest kNN size stable to adding RMT-null PCs."""

    if z_signal.shape[1] == 0 or z_signal.shape[0] < 3:
        return None, []

    z_signal = standardize_embedding(z_signal)
    if z_noise is not None and z_noise.size > 0:
        z_augmented = np.column_stack([z_signal, standardize_embedding(z_noise)])
    else:
        z_augmented = z_signal

    max_k = max(1, z_signal.shape[0] - 1)
    candidate_grid = sorted({int(k) for k in grid if 1 <= int(k) <= max_k})
    if not candidate_grid:
        candidate_grid = [min(max_k, max(2, int(np.sqrt(z_signal.shape[0]))))]

    raw_records: list[NeighborRecord] = []
    for k in candidate_grid:
        score = median_neighbor_jaccard(z_signal, z_augmented, k)
        raw_records.append(NeighborRecord(n_neighbors=k, median_jaccard=score))

    eligible = [record for record in raw_records if record.median_jaccard >= threshold]
    selected_k = eligible[0].n_neighbors if eligible else max(raw_records, key=lambda r: r.median_jaccard).n_neighbors
    records = [
        NeighborRecord(r.n_neighbors, r.median_jaccard, selected=(r.n_neighbors == selected_k))
        for r in raw_records
    ]
    return selected_k, records


def choose_kmeans_clusters(
    z_signal: np.ndarray,
    z_noise: np.ndarray | None = None,
    cluster_grid: tuple[int, ...] = tuple(range(2, 16)),
    stability_threshold: float = 0.85,
    min_cluster_fraction: float = 0.02,
    random_state: int = 0,
) -> tuple[int | None, list[ClusterRecord]]:
    """Fallback cluster-count guard using KMeans stability to noise PCs."""

    if z_signal.shape[1] == 0 or z_signal.shape[0] < 4:
        return None, []

    z_signal = standardize_embedding(z_signal)
    if z_noise is not None and z_noise.size > 0:
        z_augmented = np.column_stack([z_signal, standardize_embedding(z_noise)])
    else:
        z_augmented = z_signal

    n_cells = z_signal.shape[0]
    records: list[ClusterRecord] = []
    for k in cluster_grid:
        k = int(k)
        if k < 2 or k >= n_cells:
            continue
        labels_signal = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit_predict(z_signal)
        labels_aug = KMeans(n_clusters=k, n_init=20, random_state=random_state).fit_predict(z_augmented)
        ari = float(adjusted_rand_score(labels_signal, labels_aug))
        counts = np.bincount(labels_signal, minlength=k)
        min_frac = float(np.min(counts) / n_cells)
        try:
            sil = float(silhouette_score(z_signal, labels_signal))
        except ValueError:
            sil = float("nan")
        records.append(
            ClusterRecord(
                n_clusters=k,
                stability_ari=ari,
                min_cluster_fraction=min_frac,
                silhouette=sil,
            )
        )

    if not records:
        return None, []

    eligible = [
        r for r in records
        if r.stability_ari >= stability_threshold and r.min_cluster_fraction >= min_cluster_fraction
    ]
    if eligible:
        selected = max(eligible, key=lambda r: (np.nan_to_num(r.silhouette, nan=-np.inf), r.stability_ari, -r.n_clusters))
    else:
        selected = max(records, key=lambda r: (r.stability_ari, np.nan_to_num(r.silhouette, nan=-np.inf), -r.n_clusters))

    marked = [
        ClusterRecord(
            n_clusters=r.n_clusters,
            stability_ari=r.stability_ari,
            min_cluster_fraction=r.min_cluster_fraction,
            silhouette=r.silhouette,
            selected=(r.n_clusters == selected.n_clusters),
        )
        for r in records
    ]
    return selected.n_clusters, marked


def consensus_cluster_labels(
    z_signal: np.ndarray,
    n_clusters: int,
    n_repeats: int = 20,
    sample_fraction: float = 0.8,
    random_state: int = 0,
) -> np.ndarray:
    """Cluster cells from a co-association matrix built by repeated subsampling."""

    if z_signal.shape[1] == 0:
        return np.zeros(z_signal.shape[0], dtype=int)
    z = standardize_embedding(z_signal)
    n_cells = z.shape[0]
    n_clusters = int(min(max(2, n_clusters), max(2, n_cells - 1)))
    rng = np.random.default_rng(random_state)
    coassoc = np.zeros((n_cells, n_cells), dtype=float)
    observed = np.zeros((n_cells, n_cells), dtype=float)
    sample_size = min(n_cells, max(n_clusters + 1, int(round(n_cells * sample_fraction))))

    for repeat in range(max(1, int(n_repeats))):
        selected = np.sort(rng.choice(n_cells, size=sample_size, replace=False))
        labels = KMeans(
            n_clusters=n_clusters,
            n_init=10,
            random_state=random_state + repeat,
        ).fit_predict(z[selected])
        same = labels[:, None] == labels[None, :]
        coassoc[np.ix_(selected, selected)] += same.astype(float)
        observed[np.ix_(selected, selected)] += 1.0

    consensus = np.divide(coassoc, observed, out=np.eye(n_cells, dtype=float), where=observed > 0)
    consensus = np.maximum(consensus, consensus.T)
    np.fill_diagonal(consensus, 1.0)
    try:
        return SpectralClustering(
            n_clusters=n_clusters,
            affinity="precomputed",
            assign_labels="kmeans",
            random_state=random_state,
        ).fit_predict(consensus)
    except Exception:
        distance = 1.0 - consensus
        return AgglomerativeClustering(
            n_clusters=n_clusters,
            metric="precomputed",
            linkage="average",
        ).fit_predict(distance)


def graph_modularity_labels(z_signal: np.ndarray, n_neighbors: int, resolution: float = 1.0) -> np.ndarray:
    """Cluster a kNN graph using greedy modularity communities."""

    if z_signal.shape[1] == 0:
        return np.zeros(z_signal.shape[0], dtype=int)
    try:
        import networkx as nx
    except ImportError as exc:
        raise ImportError("networkx is required for graph_modularity resolution_rule") from exc

    z = standardize_embedding(z_signal)
    n_cells = z.shape[0]
    if n_cells < 3:
        return np.zeros(n_cells, dtype=int)
    k = min(max(1, int(n_neighbors)), n_cells - 1)
    graph = kneighbors_graph(z, n_neighbors=k, mode="connectivity", include_self=False)
    graph = graph.maximum(graph.T)
    network = nx.from_scipy_sparse_array(graph)
    communities = list(nx.community.greedy_modularity_communities(network, resolution=float(resolution)))
    labels = np.zeros(n_cells, dtype=int)
    for community_id, nodes in enumerate(communities):
        labels[list(nodes)] = community_id
    return labels


def choose_graph_modularity_clusters(
    z_signal: np.ndarray,
    z_noise: np.ndarray | None,
    n_neighbors: int | None,
    resolution_grid: tuple[float, ...] = (1.0, 1.5, 2.0, 3.0),
    stability_threshold: float = 0.80,
    min_cluster_fraction: float = 0.02,
) -> tuple[np.ndarray, list[dict]]:
    """Select a graph modularity resolution stable to adding RMT-null PCs."""

    if z_signal.shape[1] == 0 or z_signal.shape[0] < 3:
        return np.zeros(z_signal.shape[0], dtype=int), []

    z_signal = standardize_embedding(z_signal)
    if z_noise is not None and z_noise.size > 0:
        z_augmented = np.column_stack([z_signal, standardize_embedding(z_noise)])
    else:
        z_augmented = z_signal
    k = n_neighbors if n_neighbors is not None else min(50, max(2, z_signal.shape[0] - 1))
    records = []
    labels_by_resolution = {}
    if len(resolution_grid) == 1:
        resolution = float(resolution_grid[0])
        labels_signal = graph_modularity_labels(z_signal, k, resolution=resolution)
        _, counts = np.unique(labels_signal, return_counts=True)
        records.append(
            {
                "method": "graph_modularity",
                "resolution": resolution,
                "n_clusters": int(np.unique(labels_signal).size),
                "stability_ari": float("nan"),
                "min_cluster_fraction": float(np.min(counts) / z_signal.shape[0]),
                "selected": True,
            }
        )
        return labels_signal, records

    for resolution in resolution_grid:
        labels_signal = graph_modularity_labels(z_signal, k, resolution=resolution)
        labels_augmented = graph_modularity_labels(z_augmented, k, resolution=resolution)
        ari = float(adjusted_rand_score(labels_signal, labels_augmented))
        _, counts = np.unique(labels_signal, return_counts=True)
        min_frac = float(np.min(counts) / z_signal.shape[0])
        n_clusters = int(np.unique(labels_signal).size)
        record = {
            "method": "graph_modularity",
            "resolution": float(resolution),
            "n_clusters": n_clusters,
            "stability_ari": ari,
            "min_cluster_fraction": min_frac,
            "selected": False,
        }
        records.append(record)
        labels_by_resolution[float(resolution)] = labels_signal

    eligible = [
        r for r in records
        if r["stability_ari"] >= stability_threshold and r["min_cluster_fraction"] >= min_cluster_fraction
    ]
    if eligible:
        selected = max(eligible, key=lambda r: (r["resolution"], r["stability_ari"]))
    else:
        selected = max(records, key=lambda r: (r["stability_ari"], r["resolution"]))
    for record in records:
        record["selected"] = record["resolution"] == selected["resolution"]
    return labels_by_resolution[selected["resolution"]], records

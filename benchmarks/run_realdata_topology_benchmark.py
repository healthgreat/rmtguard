#!/usr/bin/env python
"""Run annotation-derived real-data topology checks for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Add a public real-data topology monitor using Paul15 hematopoiesis
labels, complementing the synthetic CONCORD-style topology stress benchmark.
Data source: data/processed/paul15_hematopoiesis.h5ad.
Method notes: The Paul15 labels define a coarse annotation-derived reference
tree. This is a topology monitor for benchmark interpretation, not a claim that
RMTGuard performs de novo trajectory inference or discovers a new lineage.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import sparse
from scipy.sparse.csgraph import shortest_path
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from rmtguard import RMTGuard, RMTGuardConfig
from rmtguard.cluster import graph_modularity_labels


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "processed" / "paul15_hematopoiesis.h5ad"
DEFAULT_OUTDIR = ROOT / "results" / "realdata_topology"
DEFAULT_DOC = ROOT / "docs" / "realdata_topology_benchmark_2026-05-12.md"
DEFAULT_SUBMISSION = ROOT / "results" / "submission" / "realdata_topology_summary.tsv"
DEFAULT_SOURCE = (
    ROOT / "results" / "figures" / "source_data" / "figure_realdata_topology_source.tsv"
)
DEFAULT_FIG_DIR = ROOT / "figures" / "manuscript"

REFERENCE_EDGES = [
    ("7MEP", "1Ery"),
    ("1Ery", "2Ery"),
    ("2Ery", "3Ery"),
    ("3Ery", "4Ery"),
    ("4Ery", "5Ery"),
    ("5Ery", "6Ery"),
    ("7MEP", "8Mk"),
    ("7MEP", "9GMP"),
    ("9GMP", "10GMP"),
    ("10GMP", "11DC"),
    ("10GMP", "12Baso"),
    ("12Baso", "13Baso"),
    ("10GMP", "14Mo"),
    ("14Mo", "15Mo"),
    ("10GMP", "16Neu"),
    ("16Neu", "17Neu"),
    ("10GMP", "18Eos"),
    ("9GMP", "19Lymph"),
]

ORDERED_CHAINS = {
    "erythroid": ["7MEP", "1Ery", "2Ery", "3Ery", "4Ery", "5Ery", "6Ery"],
    "megakaryocyte": ["7MEP", "8Mk"],
    "monocyte": ["9GMP", "10GMP", "14Mo", "15Mo"],
    "neutrophil": ["9GMP", "10GMP", "16Neu", "17Neu"],
    "basophil": ["9GMP", "10GMP", "12Baso", "13Baso"],
    "eosinophil": ["9GMP", "10GMP", "18Eos"],
    "dendritic": ["9GMP", "10GMP", "11DC"],
    "lymphoid_monitor": ["9GMP", "19Lymph"],
}

BROAD_LINEAGE = {
    "1Ery": "erythroid",
    "2Ery": "erythroid",
    "3Ery": "erythroid",
    "4Ery": "erythroid",
    "5Ery": "erythroid",
    "6Ery": "erythroid",
    "7MEP": "mep",
    "8Mk": "megakaryocyte",
    "9GMP": "gmp",
    "10GMP": "gmp",
    "11DC": "dendritic",
    "12Baso": "basophil",
    "13Baso": "basophil",
    "14Mo": "monocyte",
    "15Mo": "monocyte",
    "16Neu": "neutrophil",
    "17Neu": "neutrophil",
    "18Eos": "eosinophil",
    "19Lymph": "lymphoid",
}

METHOD_LABELS = {
    "rmtguard": "RMTGuard",
    "rmtguard_strict_signal": "RMTGuard strict",
    "fixed_pcs_30": "Fixed 30 PCs",
    "fixed_pcs_50": "Fixed 50 PCs",
}

METHOD_COLORS = {
    "rmtguard": "#1B7837",
    "rmtguard_strict_signal": "#5AAE61",
    "fixed_pcs_30": "#9970AB",
    "fixed_pcs_50": "#8073AC",
}


@dataclass(frozen=True)
class MethodOutput:
    method: str
    embedding: np.ndarray
    cluster_labels: np.ndarray
    analysis_status: str
    no_call_reason: str
    n_signal_pcs: int
    n_embedding_pcs: int
    selected_hvg_n: int
    runtime_seconds: float
    peak_memory_mb: float


def _write_tsv_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = sorted({key for row in rows for key in row}) if rows else ["empty"]
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(path)


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    tmp.replace(path)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _to_dense(x: Any) -> np.ndarray:
    if sparse.issparse(x):
        x = x.toarray()
    return np.asarray(x, dtype=float)


def _normalize_log(x: np.ndarray, target_sum: float = 1e4) -> np.ndarray:
    library = np.maximum(x.sum(axis=1, keepdims=True), 1.0)
    return np.log1p(x / library * target_sum)


def _reference_nodes(labels: np.ndarray) -> list[str]:
    observed = set(map(str, labels))
    edge_nodes = set()
    for left, right in REFERENCE_EDGES:
        edge_nodes.add(left)
        edge_nodes.add(right)
    return sorted(observed.intersection(edge_nodes), key=_node_sort_key)


def _node_sort_key(label: str) -> tuple[int, str]:
    prefix = ""
    for char in label:
        if char.isdigit():
            prefix += char
        else:
            break
    return (int(prefix) if prefix else 999, label)


def _reference_distance_lookup(labels: np.ndarray) -> dict[tuple[str, str], float]:
    nodes = _reference_nodes(labels)
    index = {node: idx for idx, node in enumerate(nodes)}
    adjacency = np.full((len(nodes), len(nodes)), np.inf, dtype=float)
    np.fill_diagonal(adjacency, 0.0)
    for left, right in REFERENCE_EDGES:
        if left in index and right in index:
            i = index[left]
            j = index[right]
            adjacency[i, j] = 1.0
            adjacency[j, i] = 1.0
    distances = shortest_path(adjacency, directed=False, unweighted=True)
    lookup: dict[tuple[str, str], float] = {}
    for left, i in index.items():
        for right, j in index.items():
            lookup[(left, right)] = float(distances[i, j])
    return lookup


def _knn_indices(x: np.ndarray, k: int) -> np.ndarray:
    if x.shape[0] <= 1:
        return np.empty((x.shape[0], 0), dtype=int)
    k = min(max(1, int(k)), x.shape[0] - 1)
    return NearestNeighbors(n_neighbors=k + 1).fit(x).kneighbors(return_distance=False)[:, 1:]


def _centroid_distance_spearman(embedding: np.ndarray, labels: np.ndarray) -> float:
    nodes = _reference_nodes(labels)
    if embedding.shape[1] == 0 or len(nodes) < 4:
        return float("nan")
    lookup = _reference_distance_lookup(labels)
    centroids = {
        node: embedding[np.asarray(labels) == node].mean(axis=0)
        for node in nodes
        if np.any(np.asarray(labels) == node)
    }
    ref_dist: list[float] = []
    embed_dist: list[float] = []
    for i, left in enumerate(nodes):
        for right in nodes[i + 1 :]:
            tree_dist = lookup.get((left, right), math.inf)
            if not math.isfinite(tree_dist):
                continue
            ref_dist.append(float(tree_dist))
            embed_dist.append(float(np.linalg.norm(centroids[left] - centroids[right])))
    if len(ref_dist) < 6:
        return float("nan")
    rho = spearmanr(ref_dist, embed_dist, nan_policy="omit").statistic
    return float(rho) if np.isfinite(rho) else float("nan")


def _reference_edge_recall(embedding: np.ndarray, labels: np.ndarray, k: int) -> float:
    nodes = _reference_nodes(labels)
    if embedding.shape[1] == 0 or len(nodes) < 4:
        return float("nan")
    present = set(nodes)
    reference_edges = {
        tuple(sorted((left, right)))
        for left, right in REFERENCE_EDGES
        if left in present and right in present
    }
    if not reference_edges:
        return float("nan")
    centroids = np.vstack([embedding[np.asarray(labels) == node].mean(axis=0) for node in nodes])
    neighbor_idx = _knn_indices(centroids, k)
    embed_edges: set[tuple[str, str]] = set()
    for idx, neighbors in enumerate(neighbor_idx):
        for neighbor in neighbors:
            embed_edges.add(tuple(sorted((nodes[idx], nodes[int(neighbor)]))))
    return float(len(reference_edges.intersection(embed_edges)) / len(reference_edges))


def _neighbor_tree_distance(embedding: np.ndarray, labels: np.ndarray, k: int) -> float:
    if embedding.shape[1] == 0 or embedding.shape[0] < 3:
        return float("nan")
    lookup = _reference_distance_lookup(labels)
    neighbor_idx = _knn_indices(embedding, k)
    distances: list[float] = []
    for idx, neighbors in enumerate(neighbor_idx):
        left = str(labels[idx])
        for neighbor in neighbors:
            right = str(labels[int(neighbor)])
            value = lookup.get((left, right), math.nan)
            if math.isfinite(value):
                distances.append(float(value))
    return float(np.mean(distances)) if distances else float("nan")


def _neighbor_same_lineage_rate(embedding: np.ndarray, labels: np.ndarray, k: int) -> float:
    if embedding.shape[1] == 0 or embedding.shape[0] < 3:
        return float("nan")
    neighbor_idx = _knn_indices(embedding, k)
    labels = np.asarray(labels).astype(str)
    rates: list[float] = []
    for idx, neighbors in enumerate(neighbor_idx):
        left = BROAD_LINEAGE.get(labels[idx], labels[idx])
        right = [BROAD_LINEAGE.get(labels[int(neighbor)], labels[int(neighbor)]) for neighbor in neighbors]
        rates.append(float(np.mean([left == item for item in right])))
    return float(np.mean(rates)) if rates else float("nan")


def _lineage_order_spearman(embedding: np.ndarray, labels: np.ndarray) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    labels = np.asarray(labels).astype(str)
    scores: list[float] = []
    for chain in ORDERED_CHAINS.values():
        order = {label: idx for idx, label in enumerate(chain)}
        mask = np.isin(labels, list(order))
        if int(mask.sum()) < 20 or len(set(labels[mask])) < 3:
            continue
        ordered_values = np.asarray([order[label] for label in labels[mask]], dtype=float)
        axis = PCA(n_components=1, random_state=0).fit_transform(embedding[mask]).ravel()
        rho = spearmanr(ordered_values, axis, nan_policy="omit").statistic
        if np.isfinite(rho):
            scores.append(abs(float(rho)))
    return float(np.mean(scores)) if scores else float("nan")


def _rmtguard_config(args: argparse.Namespace, method: str, seed: int) -> RMTGuardConfig:
    embedding_rule = "strict_signal" if method == "rmtguard_strict_signal" else "adaptive_near_edge"
    return RMTGuardConfig(
        hvg_grid=tuple(args.hvg_grid),
        max_pcs=args.max_pcs,
        embedding_rule=embedding_rule,
        embedding_source=args.embedding_source,
        graph_resolution_grid=tuple(args.graph_resolution_grid),
        resolution_rule="graph_modularity",
        n_permutations=args.n_permutations,
        random_state=seed,
        cluster_stability_threshold=args.cluster_stability_threshold,
        neighbor_stability_threshold=args.neighbor_stability_threshold,
        rare_state_guard="off",
    )


def _fit_rmtguard(x: np.ndarray, args: argparse.Namespace, method: str, seed: int) -> MethodOutput:
    tracemalloc.start()
    start = time.perf_counter()
    result = RMTGuard(_rmtguard_config(args, method, seed)).fit(
        x,
        benchmark_metadata={"dataset_id": "paul15_hematopoiesis", "method": method},
    )
    elapsed = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return MethodOutput(
        method=method,
        embedding=np.asarray(result.embedding, dtype=float),
        cluster_labels=np.asarray(result.cluster_labels),
        analysis_status=result.analysis_status,
        no_call_reason=result.no_call_reason,
        n_signal_pcs=int(result.n_signal_pcs),
        n_embedding_pcs=int(result.n_embedding_pcs),
        selected_hvg_n=int(result.selected_hvg_n),
        runtime_seconds=float(result.benchmark_metadata.get("runtime_seconds", elapsed)),
        peak_memory_mb=float(peak_bytes / (1024**2)),
    )


def _fit_fixed_pca(x: np.ndarray, args: argparse.Namespace, method: str, n_pcs: int, seed: int) -> MethodOutput:
    tracemalloc.start()
    start = time.perf_counter()
    x_scaled = StandardScaler().fit_transform(_normalize_log(x))
    n_components = min(int(n_pcs), x_scaled.shape[0] - 1, x_scaled.shape[1])
    embedding = PCA(n_components=n_components, random_state=seed).fit_transform(x_scaled)
    try:
        labels = graph_modularity_labels(
            embedding,
            n_neighbors=min(args.graph_neighbors, embedding.shape[0] - 1),
            resolution=float(args.fixed_pca_resolution),
        )
    except Exception:
        labels = np.zeros(embedding.shape[0], dtype=int)
    elapsed = time.perf_counter() - start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return MethodOutput(
        method=method,
        embedding=embedding,
        cluster_labels=np.asarray(labels),
        analysis_status="ok",
        no_call_reason="",
        n_signal_pcs=n_components,
        n_embedding_pcs=n_components,
        selected_hvg_n=x_scaled.shape[1],
        runtime_seconds=float(elapsed),
        peak_memory_mb=float(peak_bytes / (1024**2)),
    )


def _fit_method(x: np.ndarray, args: argparse.Namespace, method: str, seed: int) -> MethodOutput:
    if method in {"rmtguard", "rmtguard_strict_signal"}:
        return _fit_rmtguard(x, args, method, seed)
    if method == "fixed_pcs_30":
        return _fit_fixed_pca(x, args, method, 30, seed)
    if method == "fixed_pcs_50":
        return _fit_fixed_pca(x, args, method, 50, seed)
    raise KeyError(f"Unknown method: {method}")


def _metrics(
    dataset_id: str,
    labels: np.ndarray,
    output: MethodOutput,
    args: argparse.Namespace,
    repeat: int,
    seed: int,
) -> dict[str, Any]:
    cluster_labels = np.asarray(output.cluster_labels)
    return {
        "dataset_id": dataset_id,
        "repeat": repeat,
        "seed": seed,
        "method": output.method,
        "method_label": METHOD_LABELS.get(output.method, output.method),
        "analysis_status": output.analysis_status,
        "no_call_reason": output.no_call_reason,
        "n_cells": int(len(labels)),
        "n_reference_labels": int(pd.Series(labels).nunique()),
        "n_signal_pcs": int(output.n_signal_pcs),
        "n_embedding_pcs": int(output.n_embedding_pcs),
        "selected_hvg_n": int(output.selected_hvg_n),
        "cluster_n": int(pd.Series(cluster_labels).nunique()),
        "annotation_ari": float(adjusted_rand_score(labels.astype(str), cluster_labels.astype(str)))
        if len(set(cluster_labels)) > 1
        else float("nan"),
        "annotation_nmi": float(
            normalized_mutual_info_score(labels.astype(str), cluster_labels.astype(str))
        )
        if len(set(cluster_labels)) > 1
        else float("nan"),
        "centroid_tree_spearman": _centroid_distance_spearman(output.embedding, labels),
        "reference_edge_recall": _reference_edge_recall(
            output.embedding, labels, args.centroid_neighbor_k
        ),
        "neighbor_tree_distance": _neighbor_tree_distance(
            output.embedding, labels, args.topology_neighbors
        ),
        "neighbor_same_lineage_rate": _neighbor_same_lineage_rate(
            output.embedding, labels, args.topology_neighbors
        ),
        "lineage_order_spearman_abs": _lineage_order_spearman(output.embedding, labels),
        "runtime_seconds": float(output.runtime_seconds),
        "peak_memory_mb": float(output.peak_memory_mb),
    }


def _mean_ci(values: pd.Series) -> pd.Series:
    arr = pd.to_numeric(values, errors="coerce").to_numpy(dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return pd.Series({"mean": math.nan, "sd": math.nan, "ci95_low": math.nan, "ci95_high": math.nan})
    mean = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    half = float(1.96 * sd / math.sqrt(arr.size)) if arr.size > 1 else 0.0
    return pd.Series({"mean": mean, "sd": sd, "ci95_low": mean - half, "ci95_high": mean + half})


def _summarize(detail: pd.DataFrame) -> pd.DataFrame:
    metric_cols = [
        "annotation_ari",
        "annotation_nmi",
        "centroid_tree_spearman",
        "reference_edge_recall",
        "neighbor_tree_distance",
        "neighbor_same_lineage_rate",
        "lineage_order_spearman_abs",
        "cluster_n",
        "n_signal_pcs",
        "n_embedding_pcs",
        "selected_hvg_n",
        "runtime_seconds",
        "peak_memory_mb",
    ]
    rows: list[dict[str, Any]] = []
    for (dataset_id, method), frame in detail.groupby(["dataset_id", "method"], sort=True):
        row: dict[str, Any] = {
            "dataset_id": dataset_id,
            "method": method,
            "method_label": METHOD_LABELS.get(method, method),
            "n_repeats": int(frame["repeat"].nunique()),
            "ok_rate": float(np.mean(frame["analysis_status"].astype(str) == "ok")),
            "no_call_rate": float(np.mean(frame["analysis_status"].astype(str) != "ok")),
        }
        for metric in metric_cols:
            stats = _mean_ci(frame[metric])
            for suffix, value in stats.items():
                row[f"{metric}_{suffix}"] = value
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.sort_values(["dataset_id", "method"]).reset_index(drop=True)


def _status_label(row: pd.Series) -> str:
    if row["method"] != "rmtguard":
        return "comparator"
    tree = float(row.get("centroid_tree_spearman_mean", math.nan))
    edge = float(row.get("reference_edge_recall_mean", math.nan))
    lineage = float(row.get("neighbor_same_lineage_rate_mean", math.nan))
    if tree >= 0.45 and edge >= 0.35 and lineage >= 0.70:
        return "real_topology_supported_monitor"
    return "real_topology_caveat"


def _build_doc(
    summary: pd.DataFrame,
    detail_path: Path,
    summary_path: Path,
    source_path: Path,
    figure_paths: list[Path],
    args: argparse.Namespace,
) -> str:
    display = summary.copy()
    display["status_label"] = display.apply(_status_label, axis=1)
    table_rows = []
    for row in display.itertuples(index=False):
        table_rows.append(
            "| {method} | {tree:.3f} | {edge:.3f} | {dist:.3f} | {lineage:.3f} | {ari:.3f} | {clusters:.2f} | {status} |".format(
                method=row.method_label,
                tree=float(row.centroid_tree_spearman_mean),
                edge=float(row.reference_edge_recall_mean),
                dist=float(row.neighbor_tree_distance_mean),
                lineage=float(row.neighbor_same_lineage_rate_mean),
                ari=float(row.annotation_ari_mean),
                clusters=float(row.cluster_n_mean),
                status=row.status_label,
            )
        )
    return "\n".join(
        [
            "# Real-data topology benchmark on Paul15 hematopoiesis",
            "",
            "Date: 2026-05-12",
            "Project: RMTGuard",
            "",
            "## Scope",
            "",
            "- Dataset: `paul15_hematopoiesis` from the prepared public h5ad input.",
            f"- Repeats: `{args.n_repeats}` subsampling repeats.",
            f"- Subsampling fraction: `{args.sample_fraction}`.",
            f"- Methods: `{', '.join(args.methods)}`.",
            "- Reference: annotation-derived Paul15 cluster/lineage graph, not",
            "  experimentally measured pseudotime.",
            "",
            "## Summary Table",
            "",
            "| Method | Tree rho | Edge recall | Neighbor tree distance | Same-lineage kNN | Annotation ARI | Mean clusters | Status |",
            "|---|---:|---:|---:|---:|---:|---:|---|",
            *table_rows,
            "",
            "## Interpretation Boundary",
            "",
            "- This is a real public-data topology monitor, not a de novo trajectory",
            "  inference claim.",
            "- The Paul15 cluster graph is annotation-derived. It can support a",
            "  manuscript statement that RMTGuard was checked against a known",
            "  hematopoietic annotation structure, but it cannot prove new lineage",
            "  biology.",
            "- Use these results to strengthen the benchmark evidence arc only if the",
            "  figure and source data remain claim-bounded.",
            "",
            "## Outputs",
            "",
            f"- Detail table: `{_rel(detail_path)}`",
            f"- Summary table: `{_rel(summary_path)}`",
            f"- Figure source data: `{_rel(source_path)}`",
            *[f"- Figure asset: `{_rel(path)}`" for path in figure_paths],
        ]
    )


def _source_long(summary: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        ("centroid_tree_spearman", "Centroid tree rho", True),
        ("reference_edge_recall", "Reference edge recall", True),
        ("neighbor_tree_distance", "Neighbor tree distance", False),
        ("neighbor_same_lineage_rate", "Same-lineage kNN", True),
        ("annotation_ari", "Annotation ARI", True),
    ]
    rows: list[dict[str, Any]] = []
    for row in summary.itertuples(index=False):
        for metric, label, higher_is_better in metrics:
            rows.append(
                {
                    "dataset_id": row.dataset_id,
                    "method": row.method,
                    "method_label": row.method_label,
                    "metric": metric,
                    "metric_label": label,
                    "higher_is_better": higher_is_better,
                    "mean": getattr(row, f"{metric}_mean"),
                    "ci95_low": getattr(row, f"{metric}_ci95_low"),
                    "ci95_high": getattr(row, f"{metric}_ci95_high"),
                    "n_repeats": row.n_repeats,
                }
            )
    return pd.DataFrame(rows)


def _render_figure(source: pd.DataFrame, fig_dir: Path) -> list[Path]:
    fig_dir.mkdir(parents=True, exist_ok=True)
    metrics = [
        ("centroid_tree_spearman", "Centroid tree rho"),
        ("reference_edge_recall", "Reference edge recall"),
        ("neighbor_tree_distance", "Neighbor tree dist\n(lower better)"),
        ("neighbor_same_lineage_rate", "Same-lineage kNN"),
        ("annotation_ari", "Annotation ARI"),
    ]
    methods = ["rmtguard", "rmtguard_strict_signal", "fixed_pcs_30", "fixed_pcs_50"]
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8,
            "axes.titlesize": 9,
            "axes.labelsize": 8,
            "xtick.labelsize": 7,
            "ytick.labelsize": 7,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )
    fig, axes = plt.subplots(1, 5, figsize=(11.0, 2.55), sharey=False)
    for ax, (metric, title) in zip(axes, metrics):
        frame = source[source["metric"] == metric].set_index("method").reindex(methods)
        y = np.arange(len(methods))
        means = frame["mean"].astype(float).to_numpy()
        low = frame["ci95_low"].astype(float).to_numpy()
        high = frame["ci95_high"].astype(float).to_numpy()
        xerr = np.vstack([means - low, high - means])
        colors = [METHOD_COLORS.get(method, "#666666") for method in methods]
        ax.barh(y, means, color=colors, edgecolor="black", linewidth=0.4, height=0.62)
        ax.errorbar(means, y, xerr=xerr, fmt="none", ecolor="#222222", elinewidth=0.8, capsize=2)
        ax.set_title(title, fontweight="bold")
        ax.set_yticks(y)
        ax.set_yticklabels([METHOD_LABELS.get(method, method) for method in methods])
        ax.invert_yaxis()
        ax.grid(axis="x", color="#E5E7EB", linewidth=0.6)
        ax.set_axisbelow(True)
        if metric == "neighbor_tree_distance":
            ax.set_xlim(0, max(1.8, float(np.nanmax(high)) * 1.08))
        elif metric != "annotation_ari":
            ax.set_xlim(0, max(1.0, float(np.nanmax(high)) * 1.08))
        else:
            ax.set_xlim(0, max(0.5, float(np.nanmax(high)) * 1.15))
    fig.suptitle(
        "Paul15 real-data topology monitor",
        x=0.01,
        ha="left",
        fontsize=11,
        fontweight="bold",
    )
    fig.text(
        0.01,
        0.01,
        "Annotation-derived lineage graph; not a de novo trajectory-discovery claim.",
        fontsize=7,
        color="#555555",
    )
    fig.tight_layout(rect=(0, 0.08, 1, 0.90))
    outputs = [
        fig_dir / "figure_realdata_topology_benchmark.png",
        fig_dir / "figure_realdata_topology_benchmark.pdf",
        fig_dir / "figure_realdata_topology_benchmark.tiff",
    ]
    for path in outputs:
        if path.suffix == ".tiff":
            fig.savefig(path, dpi=300, bbox_inches="tight", pil_kwargs={"compression": "tiff_lzw"})
        elif path.suffix == ".png":
            fig.savefig(path, dpi=300, bbox_inches="tight")
        else:
            fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return outputs


def _write_manifest(paths: list[Path], source: Path, outdir: Path) -> Path:
    manifest = outdir / "figure_realdata_topology_manifest.tsv"
    rows = [
        {
            "asset": path.name,
            "path": _rel(path),
            "source_data": _rel(source),
            "status": "written",
        }
        for path in paths
    ]
    _write_tsv_atomic(manifest, rows)
    return manifest


def _load_existing(path: Path, force: bool) -> list[dict[str, str]]:
    if force or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--submission-summary", type=Path, default=DEFAULT_SUBMISSION)
    parser.add_argument("--figure-source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR)
    parser.add_argument("--dataset-id", default="paul15_hematopoiesis")
    parser.add_argument("--label-key", default="paul15_clusters")
    parser.add_argument("--n-repeats", type=int, default=10)
    parser.add_argument("--sample-fraction", type=float, default=0.80)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["rmtguard", "rmtguard_strict_signal", "fixed_pcs_30", "fixed_pcs_50"],
        choices=["rmtguard", "rmtguard_strict_signal", "fixed_pcs_30", "fixed_pcs_50"],
    )
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--max-pcs", type=int, default=50)
    parser.add_argument("--embedding-source", default="standard_pca", choices=["standard_pca", "rmt_scores"])
    parser.add_argument("--graph-resolution-grid", type=float, nargs="+", default=[1.0])
    parser.add_argument("--graph-neighbors", type=int, default=15)
    parser.add_argument("--fixed-pca-resolution", type=float, default=1.0)
    parser.add_argument("--topology-neighbors", type=int, default=15)
    parser.add_argument("--centroid-neighbor-k", type=int, default=3)
    parser.add_argument("--n-permutations", type=int, default=0)
    parser.add_argument("--cluster-stability-threshold", type=float, default=0.80)
    parser.add_argument("--neighbor-stability-threshold", type=float, default=0.70)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    import anndata as ad

    adata = ad.read_h5ad(args.input)
    if args.label_key not in adata.obs:
        raise KeyError(f"Missing label key in AnnData.obs: {args.label_key}")
    x_full = _to_dense(adata.X)
    labels_full = adata.obs[args.label_key].astype(str).to_numpy()

    detail_path = args.outdir / "realdata_topology_detail.tsv"
    summary_path = args.outdir / "realdata_topology_summary.tsv"
    metadata_path = args.outdir / "realdata_topology_metadata.json"
    rows: list[dict[str, Any]] = [dict(row) for row in _load_existing(detail_path, args.force)]
    done = {
        (row["method"], int(row["repeat"]))
        for row in rows
        if {"method", "repeat"}.issubset(row)
    }

    rng = np.random.default_rng(args.random_state)
    sample_n = min(x_full.shape[0], max(20, int(round(args.sample_fraction * x_full.shape[0]))))
    for repeat in range(args.n_repeats):
        indices = np.sort(rng.choice(x_full.shape[0], size=sample_n, replace=False))
        x = x_full[indices]
        labels = labels_full[indices]
        for method in args.methods:
            key = (method, repeat)
            if key in done:
                continue
            method_seed = args.random_state + repeat * 101 + args.methods.index(method) * 1009
            print(f"[realdata-topology] {method} repeat {repeat + 1}/{args.n_repeats}")
            output = _fit_method(x, args, method, method_seed)
            rows.append(_metrics(args.dataset_id, labels, output, args, repeat, method_seed))
            _write_tsv_atomic(detail_path, rows)

    detail = pd.DataFrame(rows)
    summary = _summarize(detail)
    summary_rows = summary.to_dict(orient="records")
    _write_tsv_atomic(summary_path, summary_rows)
    _write_tsv_atomic(args.submission_summary, summary_rows)
    source_long = _source_long(summary)
    _write_tsv_atomic(args.figure_source, source_long.to_dict(orient="records"))
    figure_paths = _render_figure(source_long, args.fig_dir)
    manifest = _write_manifest(figure_paths, args.figure_source, args.fig_dir)
    _write_text_atomic(
        args.doc,
        _build_doc(summary, detail_path, summary_path, args.figure_source, figure_paths + [manifest], args),
    )
    _write_json_atomic(
        metadata_path,
        {
            **vars(args),
            "detail_path": detail_path,
            "summary_path": summary_path,
            "submission_summary": args.submission_summary,
            "figure_source": args.figure_source,
            "figure_manifest": manifest,
            "figure_paths": figure_paths,
        },
    )
    print(detail_path)
    print(summary_path)
    print(args.submission_summary)
    print(args.figure_source)
    print(args.doc)
    print(manifest)
    for path in figure_paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

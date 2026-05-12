"""Run CONCORD-style topology stress benchmarks for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-12
Purpose: Stress-test whether RMTGuard embeddings preserve continuous,
branching, and loop-like biological geometry rather than only optimizing
cluster ARI.
Data source: Synthetic count matrices generated in this script.
Method notes: Topology metrics include kNN overlap against the planted latent
geometry, trustworthiness, continuity, pairwise distance rank correlation, and
cluster fragmentation monitors. These metrics are inspired by modern
single-cell embedding benchmarks, but this script is a local reproducible
stress test rather than a reimplementation of CONCORD.
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

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from scipy.stats import spearmanr
from sklearn.decomposition import PCA
from sklearn.manifold import trustworthiness
from sklearn.metrics import normalized_mutual_info_score, pairwise_distances
from sklearn.neighbors import NearestNeighbors, kneighbors_graph
from sklearn.preprocessing import StandardScaler

from rmtguard import RMTGuard, RMTGuardConfig
from rmtguard.cluster import graph_modularity_labels


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = ROOT / "results" / "topology_stress_benchmarks"
DEFAULT_DOC = ROOT / "docs" / "topology_stress_benchmark_2026-05-12.md"
DEFAULT_COMPARISON = ROOT / "results" / "submission" / "topology_stress_summary.tsv"


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    counts: np.ndarray
    latent: np.ndarray
    pseudotime: np.ndarray
    segment_labels: np.ndarray
    branch_labels: np.ndarray | None = None
    theta: np.ndarray | None = None


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


def _normalize_log(counts: np.ndarray, target_sum: float = 1e4) -> np.ndarray:
    library = np.maximum(counts.sum(axis=1, keepdims=True), 1.0)
    return np.log1p(counts / library * target_sum)


def _finalize_counts(
    rates: np.ndarray,
    rng: np.random.Generator,
    dropout_strength: float,
) -> np.ndarray:
    size_factors = rng.lognormal(mean=0.0, sigma=0.35, size=rates.shape[0])
    scaled = np.maximum(rates * size_factors[:, None], 1e-8)
    counts = rng.poisson(scaled).astype(float)
    if dropout_strength > 0:
        dropout_prob = dropout_strength * np.exp(-scaled / 1.8)
        counts[rng.random(counts.shape) < dropout_prob] = 0.0
    return counts


def _line_scenario(
    n_cells: int,
    n_genes: int,
    rng: np.random.Generator,
    dropout_strength: float,
) -> Scenario:
    t = np.sort(rng.uniform(0.0, 1.0, size=n_cells))
    order = rng.permutation(n_cells)
    t = t[order]
    base = rng.gamma(shape=1.4, scale=1.2, size=n_genes) + 0.03
    rates = np.tile(base, (n_cells, 1))
    block = max(10, min(60, n_genes // 10))
    rates[:, :block] *= 1.0 + 4.0 * (1.0 - t[:, None])
    rates[:, block : 2 * block] *= 1.0 + 4.0 * t[:, None]
    rates[:, 2 * block : 3 * block] *= 1.0 + 5.0 * np.exp(
        -((t[:, None] - 0.50) ** 2) / 0.025
    )
    latent = np.column_stack([t, np.zeros_like(t)])
    segments = np.digitize(t, bins=np.quantile(t, [0.25, 0.50, 0.75]))
    return Scenario(
        scenario_id="linear_trajectory",
        counts=_finalize_counts(rates, rng, dropout_strength),
        latent=latent,
        pseudotime=t,
        segment_labels=segments.astype(int),
    )


def _branch_scenario(
    n_cells: int,
    n_genes: int,
    rng: np.random.Generator,
    dropout_strength: float,
) -> Scenario:
    split = 0.38
    t = rng.uniform(0.0, 1.0, size=n_cells)
    branch = np.zeros(n_cells, dtype=int)
    after_split = t >= split
    branch[after_split] = rng.integers(1, 3, size=int(after_split.sum()))
    progress = np.clip((t - split) / (1.0 - split), 0.0, 1.0)
    x = np.where(after_split, 0.45 + 0.55 * progress, 0.45 * t / split)
    y = np.zeros(n_cells, dtype=float)
    y[branch == 1] = 0.45 * progress[branch == 1]
    y[branch == 2] = -0.45 * progress[branch == 2]
    latent = np.column_stack([x, y])

    base = rng.gamma(shape=1.4, scale=1.2, size=n_genes) + 0.03
    rates = np.tile(base, (n_cells, 1))
    block = max(10, min(50, n_genes // 12))
    rates[:, :block] *= 1.0 + 3.5 * t[:, None]
    rates[:, block : 2 * block] *= 1.0 + 5.0 * progress[:, None] * (branch == 1)[:, None]
    rates[:, 2 * block : 3 * block] *= 1.0 + 5.0 * progress[:, None] * (branch == 2)[:, None]
    rates[:, 3 * block : 4 * block] *= 1.0 + 3.0 * np.exp(
        -((t[:, None] - split) ** 2) / 0.015
    )
    segments = branch.copy()
    return Scenario(
        scenario_id="branching_trajectory",
        counts=_finalize_counts(rates, rng, dropout_strength),
        latent=latent,
        pseudotime=t,
        segment_labels=segments.astype(int),
        branch_labels=branch.astype(int),
    )


def _loop_scenario(
    n_cells: int,
    n_genes: int,
    rng: np.random.Generator,
    dropout_strength: float,
) -> Scenario:
    theta = np.sort(rng.uniform(0.0, 2.0 * np.pi, size=n_cells))
    order = rng.permutation(n_cells)
    theta = theta[order]
    latent = np.column_stack([np.cos(theta), np.sin(theta)])
    base = rng.gamma(shape=1.4, scale=1.2, size=n_genes) + 0.03
    rates = np.tile(base, (n_cells, 1))
    block = max(10, min(50, n_genes // 12))
    rates[:, :block] *= 1.0 + 2.5 * (np.sin(theta[:, None]) + 1.0)
    rates[:, block : 2 * block] *= 1.0 + 2.5 * (np.cos(theta[:, None]) + 1.0)
    centers = np.linspace(0.0, 2.0 * np.pi, 4, endpoint=False)
    for idx, center in enumerate(centers):
        start = (2 + idx) * block
        stop = min(start + block, n_genes)
        if start >= stop:
            break
        circular_delta = np.angle(np.exp(1j * (theta - center)))
        rates[:, start:stop] *= 1.0 + 4.0 * np.exp(-(circular_delta[:, None] ** 2) / 0.20)
    segments = np.floor(theta / (2.0 * np.pi / 8)).astype(int)
    return Scenario(
        scenario_id="cyclic_loop",
        counts=_finalize_counts(rates, rng, dropout_strength),
        latent=latent,
        pseudotime=theta / (2.0 * np.pi),
        segment_labels=segments,
        theta=theta,
    )


def _make_scenario(args: argparse.Namespace, scenario_id: str, seed: int) -> Scenario:
    rng = np.random.default_rng(seed)
    if scenario_id == "linear_trajectory":
        return _line_scenario(args.n_cells, args.n_genes, rng, args.dropout_strength)
    if scenario_id == "branching_trajectory":
        return _branch_scenario(args.n_cells, args.n_genes, rng, args.dropout_strength)
    if scenario_id == "cyclic_loop":
        return _loop_scenario(args.n_cells, args.n_genes, rng, args.dropout_strength)
    raise KeyError(f"Unknown scenario_id: {scenario_id}")


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


def _fit_rmtguard(scenario: Scenario, args: argparse.Namespace, method: str, seed: int) -> MethodOutput:
    start = time.perf_counter()
    result = RMTGuard(_rmtguard_config(args, method, seed)).fit(
        scenario.counts,
        benchmark_metadata={"scenario": scenario.scenario_id, "method": method},
    )
    elapsed = time.perf_counter() - start
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
        peak_memory_mb=float(result.benchmark_metadata.get("peak_memory_mb", math.nan)),
    )


def _fit_fixed_pca(
    scenario: Scenario,
    args: argparse.Namespace,
    method: str,
    n_pcs: int,
    seed: int,
) -> MethodOutput:
    tracemalloc.start()
    start = time.perf_counter()
    x = StandardScaler().fit_transform(_normalize_log(scenario.counts))
    n_components = min(int(n_pcs), x.shape[0] - 1, x.shape[1])
    embedding = PCA(n_components=n_components, random_state=seed).fit_transform(x)
    n_neighbors = min(max(5, args.graph_neighbors), embedding.shape[0] - 1)
    try:
        labels = graph_modularity_labels(
            embedding,
            n_neighbors=n_neighbors,
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
        selected_hvg_n=x.shape[1],
        runtime_seconds=float(elapsed),
        peak_memory_mb=float(peak_bytes / (1024**2)),
    )


def _knn_indices(x: np.ndarray, k: int) -> np.ndarray:
    k = min(max(1, int(k)), x.shape[0] - 1)
    indices = NearestNeighbors(n_neighbors=k + 1).fit(x).kneighbors(return_distance=False)
    return indices[:, 1 : k + 1]


def _mean_knn_recall(true_latent: np.ndarray, embedding: np.ndarray, k: int) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    true_idx = _knn_indices(true_latent, k)
    embed_idx = _knn_indices(embedding, k)
    scores = [
        len(set(true_idx[i]).intersection(set(embed_idx[i]))) / true_idx.shape[1]
        for i in range(true_latent.shape[0])
    ]
    return float(np.mean(scores))


def _continuity_score(true_latent: np.ndarray, embedding: np.ndarray, k: int) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    n = true_latent.shape[0]
    k = min(max(1, int(k)), n - 1)
    true_idx = _knn_indices(true_latent, k)
    embed_dist = pairwise_distances(embedding)
    embed_order = np.argsort(embed_dist, axis=1)
    ranks = np.empty((n, n), dtype=int)
    for i in range(n):
        ranks[i, embed_order[i]] = np.arange(n)
    embed_sets = [set(_knn_indices(embedding, k)[i]) for i in range(n)]
    penalty = 0.0
    for i in range(n):
        missing = set(true_idx[i]) - embed_sets[i]
        penalty += sum(ranks[i, j] - k for j in missing)
    denom = n * k * (2 * n - 3 * k - 1)
    if denom <= 0:
        return float("nan")
    return float(1.0 - (2.0 / denom) * penalty)


def _pairwise_spearman(
    true_latent: np.ndarray,
    embedding: np.ndarray,
    rng: np.random.Generator,
    max_pairs: int,
    theta: np.ndarray | None = None,
) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    n = true_latent.shape[0]
    total_pairs = n * (n - 1) // 2
    sample_n = min(max_pairs, total_pairs)
    left = rng.integers(0, n, size=sample_n)
    right = rng.integers(0, n, size=sample_n)
    keep = left != right
    left = left[keep]
    right = right[keep]
    if theta is None:
        true_dist = np.linalg.norm(true_latent[left] - true_latent[right], axis=1)
    else:
        delta = np.abs(theta[left] - theta[right])
        true_dist = np.minimum(delta, 2.0 * np.pi - delta)
    embed_dist = np.linalg.norm(embedding[left] - embedding[right], axis=1)
    rho = spearmanr(true_dist, embed_dist, nan_policy="omit").statistic
    return float(rho) if np.isfinite(rho) else float("nan")


def _pseudotime_spearman(pseudotime: np.ndarray, embedding: np.ndarray) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    axis = PCA(n_components=1, random_state=0).fit_transform(embedding).ravel()
    rho = spearmanr(pseudotime, axis, nan_policy="omit").statistic
    return float(abs(rho)) if np.isfinite(rho) else float("nan")


def _transition_rate(values: np.ndarray, labels: np.ndarray) -> float:
    order = np.argsort(values)
    ordered = labels[order]
    if ordered.size <= 1:
        return float("nan")
    return float(np.mean(ordered[1:] != ordered[:-1]))


def _graph_components(embedding: np.ndarray, k: int) -> int:
    if embedding.shape[1] == 0 or embedding.shape[0] < 3:
        return 0
    graph = kneighbors_graph(
        embedding,
        n_neighbors=min(max(1, int(k)), embedding.shape[0] - 1),
        mode="connectivity",
        include_self=False,
    )
    graph = graph.maximum(graph.T)
    return int(connected_components(graph, directed=False, return_labels=False))


def _safe_trustworthiness(true_latent: np.ndarray, embedding: np.ndarray, k: int) -> float:
    if embedding.shape[1] == 0:
        return float("nan")
    try:
        return float(trustworthiness(true_latent, embedding, n_neighbors=k))
    except Exception:
        return float("nan")


def _metrics(
    scenario: Scenario,
    output: MethodOutput,
    args: argparse.Namespace,
    seed: int,
) -> dict[str, Any]:
    embedding = np.asarray(output.embedding, dtype=float)
    rng = np.random.default_rng(seed)
    k = min(args.topology_neighbors, scenario.latent.shape[0] - 1)
    cluster_labels = np.asarray(output.cluster_labels)
    cluster_n = int(np.unique(cluster_labels).size) if cluster_labels.size else 0
    if scenario.branch_labels is not None and np.unique(cluster_labels).size > 1:
        branch_cluster_nmi = float(
            normalized_mutual_info_score(scenario.branch_labels.astype(str), cluster_labels.astype(str))
        )
    else:
        branch_cluster_nmi = float("nan")
    return {
        "scenario_id": scenario.scenario_id,
        "method": output.method,
        "analysis_status": output.analysis_status,
        "no_call_reason": output.no_call_reason,
        "n_signal_pcs": output.n_signal_pcs,
        "n_embedding_pcs": output.n_embedding_pcs,
        "selected_hvg_n": output.selected_hvg_n,
        "cluster_n": cluster_n,
        "topology_knn_recall": _mean_knn_recall(scenario.latent, embedding, k),
        "topology_trustworthiness": _safe_trustworthiness(scenario.latent, embedding, k),
        "topology_continuity": _continuity_score(scenario.latent, embedding, k),
        "pairwise_distance_spearman": _pairwise_spearman(
            scenario.latent,
            embedding,
            rng,
            args.max_pair_samples,
            theta=scenario.theta,
        ),
        "pseudotime_spearman_abs": _pseudotime_spearman(scenario.pseudotime, embedding),
        "cluster_segment_nmi": float(
            normalized_mutual_info_score(scenario.segment_labels.astype(str), cluster_labels.astype(str))
        )
        if np.unique(cluster_labels).size > 1
        else float("nan"),
        "branch_cluster_nmi": branch_cluster_nmi,
        "cluster_transition_rate": _transition_rate(scenario.pseudotime, cluster_labels),
        "embedding_graph_components": _graph_components(embedding, k),
        "runtime_seconds": output.runtime_seconds,
        "peak_memory_mb": output.peak_memory_mb,
    }


def _fit_method(
    scenario: Scenario,
    args: argparse.Namespace,
    method: str,
    seed: int,
) -> MethodOutput:
    if method in {"rmtguard", "rmtguard_strict_signal"}:
        return _fit_rmtguard(scenario, args, method, seed)
    if method == "fixed_pcs_30":
        return _fit_fixed_pca(scenario, args, method, 30, seed)
    if method == "fixed_pcs_50":
        return _fit_fixed_pca(scenario, args, method, 50, seed)
    raise KeyError(f"Unknown method: {method}")


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
        "topology_knn_recall",
        "topology_trustworthiness",
        "topology_continuity",
        "pairwise_distance_spearman",
        "pseudotime_spearman_abs",
        "cluster_segment_nmi",
        "branch_cluster_nmi",
        "cluster_transition_rate",
        "embedding_graph_components",
        "cluster_n",
        "n_embedding_pcs",
        "n_signal_pcs",
        "runtime_seconds",
        "peak_memory_mb",
    ]
    rows: list[dict[str, Any]] = []
    for (scenario_id, method), frame in detail.groupby(["scenario_id", "method"], sort=True):
        row: dict[str, Any] = {
            "scenario_id": scenario_id,
            "method": method,
            "n_repeats": int(frame["repeat"].nunique()),
            "ok_rate": float(np.mean(frame["analysis_status"].astype(str) == "ok")),
            "no_call_rate": float(np.mean(frame["analysis_status"].astype(str) != "ok")),
        }
        for metric in metric_cols:
            stats = _mean_ci(frame[metric])
            for suffix, value in stats.items():
                row[f"{metric}_{suffix}"] = value
        rows.append(row)
    return pd.DataFrame(rows)


def _status_label(row: pd.Series) -> str:
    if row.get("method") != "rmtguard":
        return "comparator"
    knn = float(row.get("topology_knn_recall_mean", math.nan))
    trust = float(row.get("topology_trustworthiness_mean", math.nan))
    cont = float(row.get("topology_continuity_mean", math.nan))
    no_call = float(row.get("no_call_rate", math.nan))
    if no_call >= 0.80:
        return "diagnostic_no_call_dominant"
    if trust >= 0.90 and cont >= 0.85 and knn >= 0.30:
        return "topology_preserved_monitor"
    return "topology_fragmentation_risk"


def _build_doc(summary: pd.DataFrame, detail_path: Path, summary_path: Path, args: argparse.Namespace) -> str:
    display = summary.copy()
    display["status_label"] = display.apply(_status_label, axis=1)
    rows = []
    for row in display.itertuples(index=False):
        rows.append(
            "| {scenario} | {method} | {knn:.3f} | {trust:.3f} | {cont:.3f} | {rho:.3f} | {clusters:.2f} | {status} |".format(
                scenario=row.scenario_id,
                method=row.method,
                knn=float(row.topology_knn_recall_mean),
                trust=float(row.topology_trustworthiness_mean),
                cont=float(row.topology_continuity_mean),
                rho=float(row.pairwise_distance_spearman_mean),
                clusters=float(row.cluster_n_mean),
                status=row.status_label,
            )
        )

    return "\n".join(
        [
            "# CONCORD-style topology stress benchmark",
            "",
            "Date: 2026-05-12",
            "Project: RMTGuard",
            "",
            "## Scope",
            "",
            f"- Scenarios: `{', '.join(args.scenarios)}`",
            f"- Methods: `{', '.join(args.methods)}`",
            f"- Repeats per scenario: `{args.n_repeats}`",
            f"- Cells/genes per run: `{args.n_cells}` / `{args.n_genes}`",
            f"- Topology kNN size: `{args.topology_neighbors}`",
            "",
            "## Summary Table",
            "",
            "| Scenario | Method | kNN recall | Trustworthiness | Continuity | Distance rho | Mean clusters | Status |",
            "|---|---|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## Interpretation Boundary",
            "",
            "- This is synthetic topology stress evidence, not proof of biological",
            "  trajectory correctness in every real dataset.",
            "- RMTGuard should be described as monitoring topology/no-call behavior;",
            "  do not claim that it is a dedicated trajectory inference method.",
            "- Strong results here support keeping Figure 2/3 topology panels in the",
            "  Nature Methods-facing evidence arc; weak results should be reported as",
            "  fragmentation risk rather than hidden.",
            "",
            "## Outputs",
            "",
            f"- Detail table: `{detail_path.as_posix()}`",
            f"- Summary table: `{summary_path.as_posix()}`",
            "",
            "## Next Use",
            "",
            "Use this report to update the CONCORD/scLENS benchmark upgrade checklist",
            "and later regenerate Figure 2/5 source-data panels after benchmark freeze.",
        ]
    )


def _load_existing(path: Path, force: bool) -> list[dict[str, str]]:
    if force or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
    parser.add_argument("--submission-summary", type=Path, default=DEFAULT_COMPARISON)
    parser.add_argument("--n-repeats", type=int, default=20)
    parser.add_argument("--n-cells", type=int, default=300)
    parser.add_argument("--n-genes", type=int, default=700)
    parser.add_argument("--dropout-strength", type=float, default=0.20)
    parser.add_argument("--random-state", type=int, default=20260427)
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=["linear_trajectory", "branching_trajectory", "cyclic_loop"],
        choices=["linear_trajectory", "branching_trajectory", "cyclic_loop"],
    )
    parser.add_argument(
        "--methods",
        nargs="+",
        default=["rmtguard", "rmtguard_strict_signal", "fixed_pcs_30", "fixed_pcs_50"],
        choices=["rmtguard", "rmtguard_strict_signal", "fixed_pcs_30", "fixed_pcs_50"],
    )
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[200, 400, 700])
    parser.add_argument("--max-pcs", type=int, default=40)
    parser.add_argument("--embedding-source", default="standard_pca", choices=["standard_pca", "rmt_scores"])
    parser.add_argument("--graph-resolution-grid", type=float, nargs="+", default=[1.0])
    parser.add_argument("--graph-neighbors", type=int, default=15)
    parser.add_argument("--fixed-pca-resolution", type=float, default=1.0)
    parser.add_argument("--topology-neighbors", type=int, default=15)
    parser.add_argument("--max-pair-samples", type=int, default=10000)
    parser.add_argument("--n-permutations", type=int, default=0)
    parser.add_argument("--cluster-stability-threshold", type=float, default=0.80)
    parser.add_argument("--neighbor-stability-threshold", type=float, default=0.70)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    detail_path = args.outdir / "topology_stress_detail.tsv"
    summary_path = args.outdir / "topology_stress_summary.tsv"
    metadata_path = args.outdir / "topology_stress_metadata.json"

    existing = _load_existing(detail_path, force=args.force)
    rows: list[dict[str, Any]] = [dict(row) for row in existing]
    done = {
        (row["scenario_id"], row["method"], int(row["repeat"]))
        for row in rows
        if {"scenario_id", "method", "repeat"}.issubset(row)
    }

    for repeat in range(args.n_repeats):
        for scenario_id in args.scenarios:
            scenario_seed = args.random_state + repeat * 101 + args.scenarios.index(scenario_id) * 17
            scenario = _make_scenario(args, scenario_id, scenario_seed)
            for method in args.methods:
                key = (scenario_id, method, repeat)
                if key in done:
                    continue
                method_seed = scenario_seed + args.methods.index(method) * 1009
                print(f"[topology] {scenario_id} {method} repeat {repeat + 1}/{args.n_repeats}")
                output = _fit_method(scenario, args, method, method_seed)
                rows.append(
                    {
                        "repeat": repeat,
                        "seed": method_seed,
                        **_metrics(scenario, output, args, method_seed),
                    }
                )
                _write_tsv_atomic(detail_path, rows)

    detail = pd.DataFrame(rows)
    summary = _summarize(detail)
    summary_rows = summary.to_dict(orient="records")
    _write_tsv_atomic(summary_path, summary_rows)
    _write_tsv_atomic(args.submission_summary, summary_rows)
    _write_text_atomic(args.doc, _build_doc(summary, detail_path, summary_path, args))
    _write_json_atomic(
        metadata_path,
        {
            **vars(args),
            "detail_path": detail_path,
            "summary_path": summary_path,
            "submission_summary": args.submission_summary,
        },
    )
    print(detail_path)
    print(summary_path)
    print(args.submission_summary)
    print(args.doc)
    print(metadata_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Core RMTGuard estimator."""

from __future__ import annotations

from dataclasses import dataclass, field
import time
import tracemalloc
from typing import Any

import numpy as np
from sklearn.cluster import KMeans

from .cluster import (
    ClusterRecord,
    NeighborRecord,
    choose_kmeans_clusters,
    choose_n_neighbors,
    choose_graph_modularity_clusters,
    consensus_cluster_labels,
    standardize_embedding,
)
from .preprocess import (
    biwhiten,
    normalize_total_log1p,
    residualize_batches,
    select_hvg_by_dispersion,
    standardize_genes,
    to_dense_array,
)
from .rmt import (
    Spectrum,
    bulk_ks_distance,
    estimate_noise_variance,
    mp_edges,
    permutation_max_edges,
    spectrum_from_matrix,
    tracy_widom_edge_proxy,
)


@dataclass(frozen=True)
class RMTGuardConfig:
    """Configuration for RMTGuard."""

    hvg_grid: tuple[int, ...] = (500, 1000, 2000)
    whiten: str = "biwhiten"
    target_sum: float = 1e4
    edge_buffer: float = 1.02
    plateau_fraction: float = 0.90
    max_pcs: int = 80
    min_embedding_pcs: int = 0
    noise_probe_pcs: int = 5
    n_neighbors_grid: tuple[int, ...] = (10, 15, 20, 30, 50)
    neighbor_stability_threshold: float = 0.70
    cluster_grid: tuple[int, ...] = tuple(range(2, 16))
    cluster_stability_threshold: float = 0.85
    min_cluster_fraction: float = 0.02
    random_state: int = 20260427
    pc_rule: str = "mp_tw"
    hvg_rule: str = "spectral_stability"
    hvg_score: str = "normalized_dispersion"
    embedding_rule: str = "adaptive_near_edge"
    embedding_source: str = "standard_pca"
    near_edge_window: float = 1.25
    embedding_stability_repeats: int = 5
    embedding_stability_threshold: float = 0.75
    embedding_subsample_fraction: float = 0.80
    low_signal_rescue_rule: str = "off"
    low_signal_rescue_max_pcs: int = 12
    low_signal_rescue_min_pcs: int = 2
    low_signal_rescue_stability_threshold: float = 0.90
    low_signal_rescue_null_permutations: int = 10
    low_signal_rescue_null_quantile: float = 0.95
    low_signal_rescue_min_eigen_ratio: float = 0.95
    resolution_rule: str = "graph_modularity"
    batch_key: str | None = None
    n_permutations: int = 0
    tw_alpha: float = 0.01
    stability_repeats: int = 5
    leiden_resolution_grid: tuple[float, ...] = (0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.5, 2.0)
    graph_resolution_grid: tuple[float, ...] = (1.0,)
    low_signal_graph_resolution: float = 1.0
    low_signal_pc_threshold: int = 3
    high_signal_graph_resolution: float = 1.5
    high_signal_pc_threshold: int = 10


@dataclass(frozen=True)
class HVGScanRecord:
    n_hvg: int
    n_signal_pcs: int
    mp_edge: float
    noise_variance: float
    bulk_ks: float
    mean_signal_excess: float
    tw_edge: float = float("nan")
    selected_edge: float = float("nan")
    signal_plateau_fraction: float = 0.0
    selected: bool = False


@dataclass(frozen=True)
class RMTGuardResult:
    selected_hvg_n: int
    hvg_indices: np.ndarray
    n_signal_pcs: int
    mp_edge: float
    noise_variance: float
    bulk_ks: float
    embedding: np.ndarray
    noise_embedding: np.ndarray
    eigenvalues: np.ndarray
    n_neighbors: int | None
    cluster_n: int | None
    cluster_labels: np.ndarray
    hvg_scan: list[HVGScanRecord] = field(default_factory=list)
    neighbor_scan: list[NeighborRecord] = field(default_factory=list)
    cluster_scan: list[ClusterRecord] = field(default_factory=list)
    pc_diagnostics: dict[str, Any] = field(default_factory=dict)
    hvg_diagnostics: dict[str, Any] = field(default_factory=dict)
    embedding_diagnostics: dict[str, Any] = field(default_factory=dict)
    resolution_scan: list[dict[str, Any]] = field(default_factory=list)
    null_calibration: dict[str, Any] = field(default_factory=dict)
    benchmark_metadata: dict[str, Any] = field(default_factory=dict)
    n_embedding_pcs: int = 0
    analysis_status: str = "ok"
    no_call_reason: str = ""


class RMTGuard:
    """Random Matrix Theory guarded parameter selector."""

    def __init__(self, config: RMTGuardConfig | None = None):
        self.config = config or RMTGuardConfig()

    def fit(
        self,
        x,
        already_log_normalized: bool = False,
        batches=None,
        benchmark_metadata: dict[str, Any] | None = None,
    ) -> RMTGuardResult:
        """Fit RMTGuard to a cell-by-gene count or log-normalized matrix."""

        self._validate_config()
        tracemalloc.start()
        started = time.perf_counter()

        counts_or_log = to_dense_array(x)
        x_log = counts_or_log if already_log_normalized else normalize_total_log1p(
            counts_or_log,
            target_sum=self.config.target_sum,
        )
        batch_labels = None if batches is None else np.asarray(batches)
        if batch_labels is not None:
            x_log = residualize_batches(x_log, batch_labels)

        hvg_scan, selected_hvg_n = self._scan_hvgs(x_log)
        hvg_indices = self._select_hvg_indices(x_log, selected_hvg_n)
        x_guarded = self._prepare_hvg_matrix(x_log[:, hvg_indices])
        spectrum = spectrum_from_matrix(x_guarded)
        pc_decision = self._classify_spectrum(spectrum, x_guarded, use_permutation=True)
        n_signal = pc_decision["n_signal_pcs"]
        bulk_ks = pc_decision["bulk_ks"]

        x_embedding = self._prepare_embedding_matrix(x_log[:, hvg_indices])
        embedding_spectrum = spectrum_from_matrix(x_embedding)
        embedding, noise_embedding, embedding_diagnostics = self._make_embeddings(
            spectrum,
            embedding_spectrum,
            pc_decision,
            x_embedding,
        )
        n_neighbors, neighbor_scan = choose_n_neighbors(
            embedding,
            noise_embedding,
            grid=self.config.n_neighbors_grid,
            threshold=self.config.neighbor_stability_threshold,
        )
        graph_resolution_scan: list[dict[str, Any]] = []
        if self.config.resolution_rule == "graph_modularity":
            cluster_labels, graph_resolution_scan = choose_graph_modularity_clusters(
                embedding,
                noise_embedding,
                n_neighbors=n_neighbors,
                resolution_grid=self._graph_resolution_grid(embedding_diagnostics),
                stability_threshold=min(self.config.cluster_stability_threshold, 0.80),
                min_cluster_fraction=self.config.min_cluster_fraction,
            )
            cluster_n = int(np.unique(cluster_labels).size)
            cluster_scan = []
        else:
            cluster_n, cluster_scan = choose_kmeans_clusters(
                embedding,
                noise_embedding,
                cluster_grid=self.config.cluster_grid,
                stability_threshold=self.config.cluster_stability_threshold,
                min_cluster_fraction=self.config.min_cluster_fraction,
                random_state=self.config.random_state,
            )
            cluster_labels = self._cluster_labels(embedding, cluster_n)
        reported_cluster_n = int(np.unique(cluster_labels).size) if cluster_n is not None else None
        analysis_status, no_call_reason = self._analysis_status(
            n_signal,
            embedding_diagnostics,
            int(embedding.shape[1]),
            reported_cluster_n,
        )

        marked_hvg_scan = self._mark_hvg_scan(hvg_scan, selected_hvg_n)
        elapsed = time.perf_counter() - started
        _, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        metadata = {
            "n_cells": int(counts_or_log.shape[0]),
            "n_genes": int(counts_or_log.shape[1]),
            "already_log_normalized": bool(already_log_normalized),
            "batch_aware": batch_labels is not None,
            "n_batches": int(np.unique(batch_labels).size) if batch_labels is not None else 0,
            "runtime_seconds": float(elapsed),
            "peak_memory_mb": float(peak_bytes / (1024**2)),
            "random_state": int(self.config.random_state),
            "pc_rule": self.config.pc_rule,
            "hvg_rule": self.config.hvg_rule,
            "hvg_score": self.config.hvg_score,
            "embedding_rule": self.config.embedding_rule,
            "embedding_source": self.config.embedding_source,
            "resolution_rule": self.config.resolution_rule,
            "stability_repeats": int(self.config.stability_repeats),
            "analysis_status": analysis_status,
            "no_call_reason": no_call_reason,
        }
        if benchmark_metadata:
            metadata.update(benchmark_metadata)

        if self.config.resolution_rule == "graph_modularity":
            resolution_scan = graph_resolution_scan
        else:
            resolution_scan = [
                {
                    "method": self.config.resolution_rule,
                    "n_clusters": r.n_clusters,
                    "stability_ari": r.stability_ari,
                    "min_cluster_fraction": r.min_cluster_fraction,
                    "silhouette": r.silhouette,
                    "selected": r.selected,
                }
                for r in cluster_scan
            ]

        return RMTGuardResult(
            selected_hvg_n=selected_hvg_n,
            hvg_indices=hvg_indices,
            n_signal_pcs=n_signal,
            mp_edge=pc_decision["mp_edge"],
            noise_variance=pc_decision["noise_variance"],
            bulk_ks=bulk_ks,
            embedding=embedding,
            noise_embedding=noise_embedding,
            eigenvalues=spectrum.eigenvalues,
            n_neighbors=n_neighbors,
            cluster_n=reported_cluster_n,
            cluster_labels=cluster_labels,
            hvg_scan=marked_hvg_scan,
            neighbor_scan=neighbor_scan,
            cluster_scan=cluster_scan,
            pc_diagnostics=pc_decision["pc_diagnostics"],
            hvg_diagnostics=self._hvg_diagnostics(marked_hvg_scan),
            embedding_diagnostics=embedding_diagnostics,
            resolution_scan=resolution_scan,
            null_calibration=pc_decision["null_calibration"],
            benchmark_metadata=metadata,
            n_embedding_pcs=int(embedding.shape[1]),
            analysis_status=analysis_status,
            no_call_reason=no_call_reason,
        )

    def _validate_config(self) -> None:
        if self.config.pc_rule not in {"mp", "mp_tw", "permutation", "mp_tw_permutation"}:
            raise ValueError("pc_rule must be one of: mp, mp_tw, permutation, mp_tw_permutation")
        if self.config.hvg_rule not in {"spectral_plateau", "spectral_stability", "dispersion"}:
            raise ValueError("hvg_rule must be one of: spectral_plateau, spectral_stability, dispersion")
        if self.config.hvg_score not in {"raw_dispersion", "normalized_dispersion"}:
            raise ValueError("hvg_score must be one of: raw_dispersion, normalized_dispersion")
        if self.config.embedding_rule not in {"adaptive_near_edge", "strict_signal"}:
            raise ValueError("embedding_rule must be one of: adaptive_near_edge, strict_signal")
        if self.config.embedding_source not in {"rmt_scores", "standard_pca"}:
            raise ValueError("embedding_source must be one of: rmt_scores, standard_pca")
        if self.config.low_signal_rescue_rule not in {"off", "stable_embedding", "null_calibrated_stable_embedding"}:
            raise ValueError("low_signal_rescue_rule must be one of: off, stable_embedding, null_calibrated_stable_embedding")
        if self.config.near_edge_window < 1.0:
            raise ValueError("near_edge_window must be at least 1.0")
        if self.config.embedding_stability_repeats < 1:
            raise ValueError("embedding_stability_repeats must be at least 1")
        if not 0.0 <= self.config.embedding_stability_threshold <= 1.0:
            raise ValueError("embedding_stability_threshold must be between 0 and 1")
        if not 0.0 < self.config.embedding_subsample_fraction <= 1.0:
            raise ValueError("embedding_subsample_fraction must be in (0, 1]")
        if self.config.resolution_rule not in {"kmeans_stability", "leiden_stability", "consensus_stability", "graph_modularity"}:
            raise ValueError("resolution_rule must be one of: kmeans_stability, leiden_stability, consensus_stability, graph_modularity")
        if self.config.low_signal_pc_threshold < 0:
            raise ValueError("low_signal_pc_threshold must be non-negative")
        if self.config.low_signal_rescue_max_pcs < 2:
            raise ValueError("low_signal_rescue_max_pcs must be at least 2")
        if self.config.low_signal_rescue_min_pcs < 2:
            raise ValueError("low_signal_rescue_min_pcs must be at least 2")
        if not 0.0 <= self.config.low_signal_rescue_stability_threshold <= 1.0:
            raise ValueError("low_signal_rescue_stability_threshold must be between 0 and 1")
        if self.config.low_signal_rescue_null_permutations < 0:
            raise ValueError("low_signal_rescue_null_permutations must be non-negative")
        if not 0.0 < self.config.low_signal_rescue_null_quantile < 1.0:
            raise ValueError("low_signal_rescue_null_quantile must be in (0, 1)")
        if not 0.0 < self.config.low_signal_rescue_min_eigen_ratio <= 1.0:
            raise ValueError("low_signal_rescue_min_eigen_ratio must be in (0, 1]")
        if self.config.n_permutations < 0:
            raise ValueError("n_permutations must be non-negative")
        if self.config.stability_repeats < 1:
            raise ValueError("stability_repeats must be at least 1")

    @staticmethod
    def _analysis_status(
        n_signal_pcs: int,
        embedding_diagnostics: dict[str, Any],
        n_embedding_pcs: int,
        cluster_n: int | None,
    ) -> tuple[str, str]:
        """Return a diagnostic status for downstream biological interpretation."""

        strict_signal = int(embedding_diagnostics.get("strict_signal_pcs", n_signal_pcs))
        accepted = int(embedding_diagnostics.get("accepted_embedding_pcs", n_embedding_pcs))
        if strict_signal < 2 and accepted == 0:
            return "diagnostic_no_call", "insufficient_signal_pcs_for_embedding"
        if n_embedding_pcs == 0:
            return "diagnostic_no_call", "empty_embedding_after_noise_guard"
        if cluster_n is None or int(cluster_n) < 2:
            return "diagnostic_no_call", "single_cluster_after_noise_guard"
        return "ok", ""

    def _scan_hvgs(self, x_log: np.ndarray) -> tuple[list[HVGScanRecord], int]:
        n_genes = x_log.shape[1]
        grid = sorted({min(int(k), n_genes) for k in self.config.hvg_grid if int(k) > 1})
        if not grid:
            grid = [n_genes]

        records: list[HVGScanRecord] = []
        for n_hvg in grid:
            indices = self._select_hvg_indices(x_log, n_hvg)
            x_guarded = self._prepare_hvg_matrix(x_log[:, indices])
            spectrum = spectrum_from_matrix(x_guarded)
            decision = self._classify_spectrum(spectrum, x_guarded, use_permutation=False)
            n_signal = int(min(decision["n_signal_pcs"], self.config.max_pcs))
            edge = decision["selected_edge"]
            if n_signal > 0:
                excess = np.mean((spectrum.eigenvalues[:n_signal] - edge) / max(edge, np.finfo(float).eps))
            else:
                excess = 0.0
            records.append(
                HVGScanRecord(
                    n_hvg=n_hvg,
                    n_signal_pcs=n_signal,
                    mp_edge=decision["mp_edge"],
                    noise_variance=decision["noise_variance"],
                    bulk_ks=decision["bulk_ks"],
                    mean_signal_excess=float(excess),
                    tw_edge=decision["tw_edge"],
                    selected_edge=edge,
                )
            )

        selected = self._select_hvg_record(records)
        return records, selected.n_hvg

    def _select_hvg_record(self, records: list[HVGScanRecord]) -> HVGScanRecord:
        if self.config.hvg_rule == "dispersion":
            return records[-1]

        max_signal = max(r.n_signal_pcs for r in records)
        if max_signal == 0:
            return min(records, key=lambda r: (np.nan_to_num(r.bulk_ks, nan=np.inf), r.n_hvg))

        if self.config.hvg_rule == "spectral_stability":
            target = max(1, int(np.floor(self.config.plateau_fraction * max_signal)))
            eligible = [r for r in records if r.n_signal_pcs >= target]
            return max(
                eligible,
                key=lambda r: (
                    r.n_hvg,
                    -abs(r.n_signal_pcs - max_signal),
                    -np.nan_to_num(r.bulk_ks, nan=np.inf),
                ),
            )

        target = max(1, int(np.ceil(self.config.plateau_fraction * max_signal)))
        eligible = [r for r in records if r.n_signal_pcs >= target]
        return min(eligible, key=lambda r: (r.n_hvg, np.nan_to_num(r.bulk_ks, nan=np.inf)))

    def _select_hvg_indices(self, x_log: np.ndarray, n_hvg: int) -> np.ndarray:
        return select_hvg_by_dispersion(x_log, n_hvg, method=self.config.hvg_score)

    def _mark_hvg_scan(self, records: list[HVGScanRecord], selected_hvg_n: int) -> list[HVGScanRecord]:
        max_signal = max((r.n_signal_pcs for r in records), default=0)
        marked = []
        for r in records:
            plateau = (r.n_signal_pcs / max_signal) if max_signal else 0.0
            marked.append(
                HVGScanRecord(
                    n_hvg=r.n_hvg,
                    n_signal_pcs=r.n_signal_pcs,
                    mp_edge=r.mp_edge,
                    noise_variance=r.noise_variance,
                    bulk_ks=r.bulk_ks,
                    mean_signal_excess=r.mean_signal_excess,
                    tw_edge=r.tw_edge,
                    selected_edge=r.selected_edge,
                    signal_plateau_fraction=float(plateau),
                    selected=(r.n_hvg == selected_hvg_n),
                )
            )
        return marked

    def _hvg_diagnostics(self, records: list[HVGScanRecord]) -> dict[str, Any]:
        selected = next((r for r in records if r.selected), None)
        return {
            "rule": self.config.hvg_rule,
            "score": self.config.hvg_score,
            "plateau_fraction": float(self.config.plateau_fraction),
            "grid": [int(r.n_hvg) for r in records],
            "signal_pcs_by_hvg": [int(r.n_signal_pcs) for r in records],
            "selected_hvg_n": int(selected.n_hvg) if selected else None,
            "selected_signal_plateau_fraction": float(selected.signal_plateau_fraction) if selected else None,
        }

    def _classify_spectrum(
        self,
        spectrum: Spectrum,
        x_guarded: np.ndarray,
        use_permutation: bool,
    ) -> dict[str, Any]:
        eigenvalues = np.asarray(spectrum.eigenvalues, dtype=float)
        sigma2 = estimate_noise_variance(eigenvalues, spectrum.aspect)
        _, mp_upper = mp_edges(spectrum.aspect, sigma2=sigma2)
        mp_edge = float(mp_upper * self.config.edge_buffer)
        tw_edge = tracy_widom_edge_proxy(
            n_cells=x_guarded.shape[0],
            n_genes=x_guarded.shape[1],
            sigma2=sigma2,
            alpha=self.config.tw_alpha,
            edge_buffer=self.config.edge_buffer,
        )

        permutation_edges = np.empty(0, dtype=float)
        if use_permutation and self.config.n_permutations > 0 and "permutation" in self.config.pc_rule:
            permutation_edges = permutation_max_edges(
                x_guarded,
                n_permutations=self.config.n_permutations,
                random_state=self.config.random_state,
            )
        permutation_edge = (
            float(np.quantile(permutation_edges, 1.0 - self.config.tw_alpha))
            if permutation_edges.size
            else float("nan")
        )

        if self.config.pc_rule == "mp":
            selected_edge = mp_edge
            calibration_method = "marchenko_pastur"
        elif self.config.pc_rule == "mp_tw":
            selected_edge = max(mp_edge, tw_edge)
            calibration_method = "marchenko_pastur_plus_tracy_widom_proxy"
        elif self.config.pc_rule == "permutation":
            selected_edge = permutation_edge if np.isfinite(permutation_edge) else max(mp_edge, tw_edge)
            calibration_method = "permutation" if np.isfinite(permutation_edge) else "fallback_mp_tw"
        else:
            selected_edge = max([x for x in (mp_edge, tw_edge, permutation_edge) if np.isfinite(x)])
            calibration_method = "mp_tw_permutation" if np.isfinite(permutation_edge) else "fallback_mp_tw"

        signal_mask = eigenvalues > selected_edge
        n_signal = int(min(np.sum(signal_mask), self.config.max_pcs))
        null_false_positive_rate = (
            float(np.mean(permutation_edges > selected_edge))
            if permutation_edges.size
            else float("nan")
        )
        bulk_ks = bulk_ks_distance(eigenvalues, spectrum.aspect, sigma2, selected_edge)

        null_calibration = {
            "method": calibration_method,
            "n_permutations": int(permutation_edges.size),
            "tw_alpha": float(self.config.tw_alpha),
            "permutation_edge": permutation_edge,
            "null_false_positive_rate": null_false_positive_rate,
            "permutation_max_edges": permutation_edges.tolist(),
        }
        pc_diagnostics = {
            "rule": self.config.pc_rule,
            "aspect": float(spectrum.aspect),
            "mp_edge": mp_edge,
            "tw_edge": float(tw_edge),
            "selected_edge": float(selected_edge),
            "noise_variance": float(sigma2),
            "bulk_ks": float(bulk_ks),
            "n_signal_pcs": int(n_signal),
            "max_pcs": int(self.config.max_pcs),
            "min_embedding_pcs": int(self.config.min_embedding_pcs),
            "top_eigenvalues": eigenvalues[: min(10, eigenvalues.size)].tolist(),
        }
        return {
            "n_signal_pcs": n_signal,
            "selected_edge": float(selected_edge),
            "mp_edge": mp_edge,
            "tw_edge": float(tw_edge),
            "noise_variance": float(sigma2),
            "bulk_ks": float(bulk_ks),
            "pc_diagnostics": pc_diagnostics,
            "null_calibration": null_calibration,
        }

    def _prepare_hvg_matrix(self, x_hvg: np.ndarray) -> np.ndarray:
        if self.config.whiten == "biwhiten":
            return biwhiten(x_hvg).x
        if self.config.whiten == "zscore":
            return standardize_genes(x_hvg)
        raise ValueError("config.whiten must be 'biwhiten' or 'zscore'")

    def _prepare_embedding_matrix(self, x_hvg: np.ndarray) -> np.ndarray:
        if self.config.embedding_source == "standard_pca":
            return standardize_genes(x_hvg)
        return self._prepare_hvg_matrix(x_hvg)

    def _graph_resolution_grid(self, embedding_diagnostics: dict[str, Any]) -> tuple[float, ...]:
        strict_signal = int(embedding_diagnostics.get("strict_signal_pcs", 0))
        if 0 < strict_signal <= self.config.low_signal_pc_threshold:
            return (float(self.config.low_signal_graph_resolution),)
        if strict_signal >= self.config.high_signal_pc_threshold:
            return (float(self.config.high_signal_graph_resolution),)
        return self.config.graph_resolution_grid

    def _make_embeddings(
        self,
        rmt_spectrum: Spectrum,
        embedding_spectrum: Spectrum,
        pc_decision: dict[str, Any],
        x_embedding: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        max_cols = min(rmt_spectrum.left_vectors.shape[1], embedding_spectrum.left_vectors.shape[1])
        n_signal = int(pc_decision["n_signal_pcs"])
        strict_count = min(n_signal, self.config.max_pcs, max_cols)
        selected_edge = float(pc_decision["selected_edge"])
        selected_indices = list(range(strict_count))
        near_edge_threshold = selected_edge / max(float(self.config.near_edge_window), 1.0)
        candidate_limit = min(max_cols, self.config.max_pcs)
        near_edge_candidates = [
            idx
            for idx in range(strict_count, candidate_limit)
            if rmt_spectrum.eigenvalues[idx] >= near_edge_threshold
        ]

        pc_records: list[dict[str, Any]] = [
            {
                "pc": int(idx + 1),
                "eigenvalue": float(rmt_spectrum.eigenvalues[idx]),
                "role": "strict_signal",
                "stability": 1.0,
                "accepted": True,
                "reason": "above_selected_edge",
            }
            for idx in selected_indices
        ]

        low_signal_rescued = False
        low_signal_stability: dict[int, float] = {}
        if strict_count < 2 and self.config.min_embedding_pcs == 0:
            if (
                self.config.low_signal_rescue_rule in {"stable_embedding", "null_calibrated_stable_embedding"}
                and self.config.embedding_rule == "adaptive_near_edge"
            ):
                rescue_limit = min(candidate_limit, int(self.config.low_signal_rescue_max_pcs))
                rescue_candidates = [idx for idx in range(strict_count, rescue_limit)]
                low_signal_stability = self._pc_subsample_stability(
                    x_embedding,
                    embedding_spectrum,
                    rescue_candidates,
                )
                null_thresholds = {}
                if self.config.low_signal_rescue_rule == "null_calibrated_stable_embedding":
                    null_thresholds = self._pc_subsample_stability_null_thresholds(
                        x_embedding,
                        rescue_candidates,
                    )
                for idx in rescue_candidates:
                    score = low_signal_stability.get(idx, float("nan"))
                    null_threshold = null_thresholds.get(idx, float("nan"))
                    eigen_ratio = float(rmt_spectrum.eigenvalues[idx] / max(selected_edge, np.finfo(float).eps))
                    edge_pass = (
                        self.config.low_signal_rescue_rule == "stable_embedding"
                        or bool(eigen_ratio >= self.config.low_signal_rescue_min_eigen_ratio)
                    )
                    null_pass = (
                        self.config.low_signal_rescue_rule == "stable_embedding"
                        or (
                            np.isfinite(null_threshold)
                            and np.isfinite(score)
                            and score > null_threshold
                        )
                    )
                    accepted = bool(
                        np.isfinite(score)
                        and score >= self.config.low_signal_rescue_stability_threshold
                        and null_pass
                        and edge_pass
                    )
                    if accepted:
                        selected_indices.append(idx)
                    reason = "stable_low_signal_embedding" if accepted else "below_low_signal_rescue_threshold"
                    if self.config.low_signal_rescue_rule == "null_calibrated_stable_embedding":
                        if accepted:
                            reason = "stable_above_permutation_null"
                        elif not edge_pass:
                            reason = "below_low_signal_edge_ratio"
                        elif np.isfinite(score) and score >= self.config.low_signal_rescue_stability_threshold and not null_pass:
                            reason = "below_low_signal_null_threshold"
                    pc_records.append(
                        {
                            "pc": int(idx + 1),
                            "eigenvalue": float(rmt_spectrum.eigenvalues[idx]),
                            "eigen_ratio_to_selected_edge": eigen_ratio,
                            "role": "low_signal_rescue_candidate",
                            "stability": float(score),
                            "null_stability_threshold": float(null_threshold),
                            "stability_null_excess": float(score - null_threshold) if np.isfinite(score) and np.isfinite(null_threshold) else float("nan"),
                            "accepted": accepted,
                            "reason": reason,
                        }
                    )
                selected_indices = sorted(set(selected_indices))
                accepted_rescue_count = sum(idx >= strict_count for idx in selected_indices)
                low_signal_rescued = accepted_rescue_count >= int(self.config.low_signal_rescue_min_pcs)

            if not low_signal_rescued:
                for record in pc_records:
                    if record["role"] == "strict_signal":
                        record["accepted"] = False
                        record["reason"] = "insufficient_signal_pcs_for_embedding"
                    if record["role"] == "low_signal_rescue_candidate" and record.get("accepted"):
                        record["accepted"] = False
                        record["reason"] = "insufficient_stable_low_signal_rescue_pcs"
                diagnostics = self._embedding_diagnostics(
                    strict_count,
                    [],
                    [],
                    near_edge_threshold,
                    pc_records,
                )
                return (
                    np.empty((embedding_spectrum.left_vectors.shape[0], 0), dtype=float),
                    np.empty((embedding_spectrum.left_vectors.shape[0], 0), dtype=float),
                    diagnostics,
                )

        near_edge_stability: dict[int, float] = {}
        if self.config.embedding_rule == "adaptive_near_edge" and near_edge_candidates:
            near_edge_stability = self._pc_subsample_stability(
                x_embedding,
                embedding_spectrum,
                near_edge_candidates,
            )
            for idx in near_edge_candidates:
                if idx in selected_indices and low_signal_rescued:
                    continue
                score = near_edge_stability.get(idx, float("nan"))
                accepted = bool(np.isfinite(score) and score >= self.config.embedding_stability_threshold)
                if accepted:
                    selected_indices.append(idx)
                pc_records.append(
                    {
                        "pc": int(idx + 1),
                        "eigenvalue": float(rmt_spectrum.eigenvalues[idx]),
                        "role": "near_edge_candidate",
                        "stability": float(score),
                        "accepted": accepted,
                        "reason": "stable_near_edge" if accepted else "below_stability_threshold",
                    }
                )
        elif self.config.embedding_rule == "strict_signal":
            for idx in near_edge_candidates:
                pc_records.append(
                    {
                        "pc": int(idx + 1),
                        "eigenvalue": float(rmt_spectrum.eigenvalues[idx]),
                        "role": "near_edge_candidate",
                        "stability": float("nan"),
                        "accepted": False,
                        "reason": "strict_signal_rule",
                    }
                )

        if self.config.min_embedding_pcs > len(selected_indices):
            forced_needed = min(self.config.min_embedding_pcs, candidate_limit) - len(selected_indices)
            forced = [idx for idx in range(candidate_limit) if idx not in selected_indices][: max(0, forced_needed)]
            for idx in forced:
                selected_indices.append(idx)
                pc_records.append(
                    {
                        "pc": int(idx + 1),
                        "eigenvalue": float(rmt_spectrum.eigenvalues[idx]),
                        "role": "forced_min_embedding",
                        "stability": near_edge_stability.get(idx, float("nan")),
                        "accepted": True,
                        "reason": "forced_by_min_embedding_pcs",
                    }
                )

        selected_indices = sorted(set(selected_indices))
        if not selected_indices:
            diagnostics = self._embedding_diagnostics(
                strict_count,
                near_edge_candidates,
                selected_indices,
                near_edge_threshold,
                pc_records,
            )
            return (
                np.empty((embedding_spectrum.left_vectors.shape[0], 0), dtype=float),
                np.empty((embedding_spectrum.left_vectors.shape[0], 0), dtype=float),
                diagnostics,
            )

        embedding = embedding_spectrum.left_vectors[:, selected_indices] * embedding_spectrum.singular_values[selected_indices]
        noise_indices = [idx for idx in range(max_cols) if idx not in selected_indices][: self.config.noise_probe_pcs]
        if noise_indices:
            noise_scores = embedding_spectrum.left_vectors[:, noise_indices] * embedding_spectrum.singular_values[noise_indices]
        else:
            noise_scores = np.empty((embedding_spectrum.left_vectors.shape[0], 0), dtype=float)
        diagnostics = self._embedding_diagnostics(
            strict_count,
            near_edge_candidates,
            selected_indices,
            near_edge_threshold,
            pc_records,
        )
        return embedding, noise_scores, diagnostics

    def _pc_subsample_stability(
        self,
        x_guarded: np.ndarray,
        spectrum: Spectrum,
        candidate_indices: list[int],
    ) -> dict[int, float]:
        n_cells = x_guarded.shape[0]
        if n_cells < 6 or not candidate_indices:
            return {idx: float("nan") for idx in candidate_indices}

        sample_size = int(round(n_cells * self.config.embedding_subsample_fraction))
        sample_size = min(n_cells - 1, max(5, sample_size))
        rng = np.random.default_rng(self.config.random_state)
        max_match_cols = min(
            spectrum.left_vectors.shape[1],
            max(candidate_indices) + 1 + self.config.noise_probe_pcs,
        )
        full_scores = spectrum.left_vectors[:, :max_match_cols] * spectrum.singular_values[:max_match_cols]
        scores = {idx: [] for idx in candidate_indices}

        for repeat in range(int(self.config.embedding_stability_repeats)):
            selected = np.sort(rng.choice(n_cells, size=sample_size, replace=False))
            sub_spectrum = spectrum_from_matrix(x_guarded[selected])
            sub_cols = min(max_match_cols, sub_spectrum.left_vectors.shape[1])
            sub_scores = sub_spectrum.left_vectors[:, :sub_cols] * sub_spectrum.singular_values[:sub_cols]
            for idx in candidate_indices:
                full_pc = full_scores[selected, idx]
                match_scores = [
                    self._safe_abs_corr(full_pc, sub_scores[:, sub_idx])
                    for sub_idx in range(sub_cols)
                ]
                scores[idx].append(max(match_scores) if match_scores else float("nan"))

        out = {}
        for idx, values in scores.items():
            finite = [value for value in values if np.isfinite(value)]
            out[idx] = float(np.median(finite)) if finite else float("nan")
        return out

    def _pc_subsample_stability_null_thresholds(
        self,
        x_guarded: np.ndarray,
        candidate_indices: list[int],
    ) -> dict[int, float]:
        if not candidate_indices or self.config.low_signal_rescue_null_permutations <= 0:
            return {idx: float("nan") for idx in candidate_indices}

        rng = np.random.default_rng(self.config.random_state + 7919)
        null_scores = {idx: [] for idx in candidate_indices}
        for repeat in range(int(self.config.low_signal_rescue_null_permutations)):
            permuted = np.asarray(x_guarded, dtype=float).copy()
            for col in range(permuted.shape[1]):
                rng.shuffle(permuted[:, col])
            null_spectrum = spectrum_from_matrix(permuted)
            scores = self._pc_subsample_stability(
                permuted,
                null_spectrum,
                candidate_indices,
            )
            for idx, score in scores.items():
                if np.isfinite(score):
                    null_scores[idx].append(float(score))

        thresholds = {}
        for idx, values in null_scores.items():
            thresholds[idx] = (
                float(np.quantile(values, self.config.low_signal_rescue_null_quantile))
                if values
                else float("nan")
            )
        return thresholds

    @staticmethod
    def _safe_abs_corr(left: np.ndarray, right: np.ndarray) -> float:
        left = np.asarray(left, dtype=float)
        right = np.asarray(right, dtype=float)
        left = left - np.mean(left)
        right = right - np.mean(right)
        left_norm = np.linalg.norm(left)
        right_norm = np.linalg.norm(right)
        if left_norm <= np.finfo(float).eps or right_norm <= np.finfo(float).eps:
            return float("nan")
        return float(abs(np.dot(left, right) / (left_norm * right_norm)))

    def _embedding_diagnostics(
        self,
        strict_count: int,
        near_edge_candidates: list[int],
        selected_indices: list[int],
        near_edge_threshold: float,
        pc_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        accepted_stabilities = [
            float(record["stability"])
            for record in pc_records
            if record.get("accepted") and np.isfinite(record.get("stability", float("nan")))
        ]
        low_signal_records = [
            record for record in pc_records
            if record.get("role") == "low_signal_rescue_candidate"
        ]
        return {
            "rule": self.config.embedding_rule,
            "source": self.config.embedding_source,
            "near_edge_window": float(self.config.near_edge_window),
            "near_edge_threshold": float(near_edge_threshold),
            "stability_repeats": int(self.config.embedding_stability_repeats),
            "stability_threshold": float(self.config.embedding_stability_threshold),
            "subsample_fraction": float(self.config.embedding_subsample_fraction),
            "low_signal_rescue_rule": self.config.low_signal_rescue_rule,
            "low_signal_rescue_min_pcs": int(self.config.low_signal_rescue_min_pcs),
            "low_signal_rescue_max_pcs": int(self.config.low_signal_rescue_max_pcs),
            "low_signal_rescue_stability_threshold": float(self.config.low_signal_rescue_stability_threshold),
            "low_signal_rescue_null_permutations": int(self.config.low_signal_rescue_null_permutations),
            "low_signal_rescue_null_quantile": float(self.config.low_signal_rescue_null_quantile),
            "low_signal_rescue_min_eigen_ratio": float(self.config.low_signal_rescue_min_eigen_ratio),
            "strict_signal_pcs": int(strict_count),
            "low_signal_pc_threshold": int(self.config.low_signal_pc_threshold),
            "low_signal_candidate_pcs": int(len(low_signal_records)),
            "accepted_low_signal_rescue_pcs": int(sum(bool(record.get("accepted")) for record in low_signal_records)),
            "near_edge_candidate_pcs": int(len(near_edge_candidates)),
            "accepted_embedding_pcs": int(len(selected_indices)),
            "accepted_pc_indices": [int(idx + 1) for idx in selected_indices],
            "near_edge_candidate_indices": [int(idx + 1) for idx in near_edge_candidates],
            "embedding_pc_stability_min": float(np.min(accepted_stabilities)) if accepted_stabilities else float("nan"),
            "embedding_pc_stability_median": float(np.median(accepted_stabilities)) if accepted_stabilities else float("nan"),
            "pc_records": pc_records,
        }

    def _cluster_labels(self, embedding: np.ndarray, cluster_n: int | None) -> np.ndarray:
        if cluster_n is None or embedding.shape[1] == 0:
            return np.zeros(embedding.shape[0], dtype=int)
        if self.config.resolution_rule == "consensus_stability":
            return consensus_cluster_labels(
                embedding,
                cluster_n,
                n_repeats=self.config.stability_repeats,
                random_state=self.config.random_state,
            )
        z = standardize_embedding(embedding)
        return KMeans(
            n_clusters=int(cluster_n),
            n_init=20,
            random_state=self.config.random_state,
        ).fit_predict(z)

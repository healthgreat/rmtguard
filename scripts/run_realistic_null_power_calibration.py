#!/usr/bin/env python
"""Run realistic null and rare-state power calibration for RMTGuard.

Author: RMTGuard development team
Date: 2026-05-02
Purpose: Stress-test RMTGuard under scRNA-seq-like count nulls that preserve
library-size, dropout, and gene-marginal structure, then estimate rare-state
recovery power across prevalence/effect-size settings.
Data source: Synthetic empirical-like count matrices generated locally with
fixed random seeds. No private or clinical data are used.
Method notes: Defaults are intentionally modest for a resumable local draft
calibration. Increase --n-repeats, --n-cells, and --n-genes before using the
tables as final manuscript-grade calibration.
"""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.preprocessing import StandardScaler

from rmtguard import RMTGuard, RMTGuardConfig

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTDIR = ROOT / "results" / "calibration"
DOC = ROOT / "docs" / "realistic_null_power_calibration.md"


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def _atomic_write_tsv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, sep="\t", index=False, quoting=csv.QUOTE_MINIMAL)
    tmp.replace(path)


def _atomic_write_text(text: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text.rstrip() + "\n", encoding="utf-8")
    tmp.replace(path)


def _empirical_like_counts(
    n_cells: int,
    n_genes: int,
    rng: np.random.Generator,
    dropout_strength: float = 0.55,
) -> np.ndarray:
    """Generate a scRNA-seq-like count matrix without cell-state structure."""

    gene_means = rng.gamma(shape=1.25, scale=1.0, size=n_genes) + 0.015
    size_factors = rng.lognormal(mean=0.0, sigma=0.55, size=n_cells)
    gamma_noise = rng.gamma(shape=2.0, scale=0.5, size=(n_cells, n_genes))
    rates = size_factors[:, None] * gene_means[None, :] * gamma_noise
    counts = rng.poisson(rates).astype(float)
    dropout_prob = dropout_strength * np.exp(-rates / 1.8)
    dropout = rng.random(counts.shape) < dropout_prob
    counts[dropout] = 0.0
    return counts


def _multinomial_library_null(
    counts: np.ndarray, rng: np.random.Generator
) -> np.ndarray:
    """Preserve each cell library size and sample genes by global frequencies."""

    libraries = counts.sum(axis=1).astype(int)
    gene_probs = counts.sum(axis=0) + 1e-6
    gene_probs = gene_probs / gene_probs.sum()
    out = np.vstack([rng.multinomial(int(lib), gene_probs) for lib in libraries])
    return out.astype(float)


def _gene_permutation_null(counts: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Permute each gene independently across cells, preserving gene marginals."""

    out = counts.copy()
    for gene_idx in range(out.shape[1]):
        out[:, gene_idx] = rng.permutation(out[:, gene_idx])
    return out.astype(float)


def _library_stratified_gene_null(
    counts: np.ndarray, rng: np.random.Generator, n_bins: int = 4
) -> np.ndarray:
    """Permute gene counts within library-size strata to retain dropout structure."""

    out = counts.copy()
    libraries = counts.sum(axis=1)
    quantiles = np.unique(np.quantile(libraries, np.linspace(0, 1, n_bins + 1)))
    if quantiles.size <= 2:
        return _gene_permutation_null(counts, rng)
    bin_ids = np.digitize(libraries, quantiles[1:-1], right=True)
    for bin_id in np.unique(bin_ids):
        cells = np.where(bin_ids == bin_id)[0]
        if cells.size <= 1:
            continue
        for gene_idx in range(out.shape[1]):
            out[cells, gene_idx] = rng.permutation(out[cells, gene_idx])
    return out.astype(float)


def _rare_state_counts(
    n_cells: int,
    n_genes: int,
    prevalence: float,
    effect_size: float,
    rng: np.random.Generator,
    markers: int = 35,
    dropout_strength: float = 0.35,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a common-state plus rare-state count matrix."""

    rare_n = max(3, int(round(n_cells * prevalence)))
    labels = np.zeros(n_cells, dtype=int)
    labels[-rare_n:] = 1
    rng.shuffle(labels)

    gene_means = rng.gamma(shape=1.25, scale=1.0, size=n_genes) + 0.015
    size_factors = rng.lognormal(mean=0.0, sigma=0.55, size=n_cells)
    gamma_noise = rng.gamma(shape=2.0, scale=0.5, size=(n_cells, n_genes))
    rates = size_factors[:, None] * gene_means[None, :] * gamma_noise
    rare_cells = labels == 1
    marker_stop = min(markers, n_genes)
    rates[np.ix_(rare_cells, np.arange(marker_stop))] *= effect_size
    rates[np.ix_(rare_cells, np.arange(marker_stop))] += (
        size_factors[rare_cells, None] * effect_size * 2.0
    )
    counts = rng.poisson(rates).astype(float)
    dropout_prob = dropout_strength * np.exp(-rates / 1.8)
    dropout = rng.random(counts.shape) < dropout_prob
    counts[dropout] = 0.0
    return counts, labels


def _config(random_state: int, args: argparse.Namespace) -> RMTGuardConfig:
    return RMTGuardConfig(
        hvg_grid=tuple(args.hvg_grid),
        max_pcs=args.max_pcs,
        pc_rule=args.pc_rule,
        hvg_rule="spectral_stability",
        hvg_score="normalized_dispersion",
        embedding_rule="adaptive_near_edge",
        embedding_source="standard_pca",
        near_edge_window=args.near_edge_window,
        embedding_stability_repeats=args.embedding_stability_repeats,
        embedding_stability_threshold=args.embedding_stability_threshold,
        embedding_subsample_fraction=0.80,
        resolution_rule="graph_modularity",
        graph_resolution_grid=(1.0,),
        rare_state_guard=args.rare_state_guard,
        rare_state_min_fraction=args.rare_state_min_fraction,
        rare_state_max_fraction=args.rare_state_max_fraction,
        rare_state_min_cells=args.rare_state_min_cells,
        rare_state_min_separation=args.rare_state_min_separation,
        rare_state_min_silhouette=args.rare_state_min_silhouette,
        n_permutations=args.n_permutations,
        tw_alpha=args.tw_alpha,
        random_state=random_state,
        cluster_grid=tuple(range(2, args.max_clusters + 1)),
    )


def _run_rmtguard(
    counts: np.ndarray,
    random_state: int,
    args: argparse.Namespace,
    metadata: dict[str, object],
) -> dict[str, object]:
    result = RMTGuard(_config(random_state, args)).fit(
        counts, benchmark_metadata=metadata
    )
    rare_guard = next(
        (
            row
            for row in result.resolution_scan
            if row.get("method") == "rare_state_guard"
        ),
        {},
    )
    return {
        "n_signal_pcs": result.n_signal_pcs,
        "accepted_embedding_pcs": result.embedding_diagnostics[
            "accepted_embedding_pcs"
        ],
        "cluster_n": result.cluster_n,
        "analysis_status": result.analysis_status,
        "no_call_reason": result.no_call_reason,
        "rare_state_guard": result.benchmark_metadata["rare_state_guard"],
        "rare_state_guard_selected": bool(rare_guard.get("selected", False)),
        "rare_state_guard_reason": rare_guard.get("reason", ""),
        "rare_state_binary_fraction": rare_guard.get(
            "binary_small_cluster_fraction", float("nan")
        ),
        "rare_state_binary_separation": rare_guard.get(
            "centroid_separation", float("nan")
        ),
        "rare_state_binary_silhouette": rare_guard.get(
            "binary_silhouette", float("nan")
        ),
        "selected_hvg_n": result.selected_hvg_n,
        "mp_edge": result.mp_edge,
        "selected_edge": result.pc_diagnostics["selected_edge"],
        "bulk_ks": result.bulk_ks,
        "null_false_positive_rate": result.null_calibration["null_false_positive_rate"],
        "runtime_seconds": result.benchmark_metadata["runtime_seconds"],
        "peak_memory_mb": result.benchmark_metadata["peak_memory_mb"],
        "cluster_labels": result.cluster_labels,
    }


def _fixed_pca_kmeans(
    counts: np.ndarray,
    labels: np.ndarray,
    n_pcs: int,
    random_state: int,
) -> dict[str, float]:
    if np.unique(labels).size < 2:
        return {"fixed_ari": math.nan, "fixed_nmi": math.nan}
    x = np.log1p(counts / np.maximum(counts.sum(axis=1, keepdims=True), 1e-12) * 1e4)
    x = StandardScaler().fit_transform(x)
    pcs = PCA(
        n_components=min(n_pcs, x.shape[0] - 1, x.shape[1]),
        random_state=random_state,
    ).fit_transform(x)
    pred = KMeans(n_clusters=2, n_init=20, random_state=random_state).fit_predict(pcs)
    return {
        "fixed_ari": float(adjusted_rand_score(labels, pred)),
        "fixed_nmi": float(normalized_mutual_info_score(labels, pred)),
        "fixed_rare_f1": _best_rare_cluster_f1(labels, pred)["rare_f1"],
    }


def _best_rare_cluster_f1(labels: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    rare_mask = labels == 1
    rare_n = int(rare_mask.sum())
    if rare_n == 0:
        return {
            "rare_precision": math.nan,
            "rare_recall": math.nan,
            "rare_f1": math.nan,
        }
    best = {"rare_precision": 0.0, "rare_recall": 0.0, "rare_f1": 0.0}
    for cluster in np.unique(pred):
        cluster_mask = pred == cluster
        tp = int(np.logical_and(cluster_mask, rare_mask).sum())
        fp = int(np.logical_and(cluster_mask, ~rare_mask).sum())
        fn = int(np.logical_and(~cluster_mask, rare_mask).sum())
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall)
            else 0.0
        )
        if f1 > best["rare_f1"]:
            best = {
                "rare_precision": float(precision),
                "rare_recall": float(recall),
                "rare_f1": float(f1),
            }
    return best


def _null_generators(
    counts: np.ndarray, rng: np.random.Generator
) -> Iterable[tuple[str, np.ndarray]]:
    yield "library_multinomial_null", _multinomial_library_null(counts, rng)
    yield "gene_permutation_null", _gene_permutation_null(counts, rng)
    yield "library_stratified_gene_null", _library_stratified_gene_null(counts, rng)


def run_null_calibration(args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for repeat in range(args.n_repeats):
        rng = np.random.default_rng(args.random_state + repeat)
        base = _empirical_like_counts(args.n_cells, args.n_genes, rng)
        for null_model, counts in _null_generators(base, rng):
            seed = args.random_state + 1000 + repeat
            result = _run_rmtguard(
                counts,
                random_state=seed,
                args=args,
                metadata={"calibration": "realistic_null", "null_model": null_model},
            )
            false_signal = int(
                float(result["n_signal_pcs"]) > args.false_signal_pc_floor
            )
            false_call = int(str(result["analysis_status"]) != "diagnostic_no_call")
            rows.append(
                {
                    "calibration_type": "realistic_null",
                    "null_model": null_model,
                    "repeat": repeat,
                    "n_cells": args.n_cells,
                    "n_genes": args.n_genes,
                    "false_signal_pc_floor": args.false_signal_pc_floor,
                    "false_signal": false_signal,
                    "false_call": false_call,
                    **{
                        key: value
                        for key, value in result.items()
                        if key != "cluster_labels"
                    },
                }
            )
    return pd.DataFrame(rows)


def run_power_grid(args: argparse.Namespace) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for prevalence in args.prevalence_grid:
        for effect_size in args.effect_size_grid:
            for repeat in range(args.n_repeats):
                rng = np.random.default_rng(
                    args.random_state
                    + 10000
                    + int(prevalence * 10000)
                    + int(effect_size * 100)
                    + repeat
                )
                counts, labels = _rare_state_counts(
                    args.n_cells,
                    args.n_genes,
                    prevalence=prevalence,
                    effect_size=effect_size,
                    rng=rng,
                )
                seed = args.random_state + 2000 + repeat
                result = _run_rmtguard(
                    counts,
                    random_state=seed,
                    args=args,
                    metadata={
                        "calibration": "rare_state_power",
                        "prevalence": prevalence,
                        "effect_size": effect_size,
                    },
                )
                pred = np.asarray(result["cluster_labels"])
                ari = float(adjusted_rand_score(labels, pred))
                nmi = float(normalized_mutual_info_score(labels, pred))
                rare_metrics = _best_rare_cluster_f1(labels, pred)
                fixed = _fixed_pca_kmeans(counts, labels, 30, seed)
                rows.append(
                    {
                        "calibration_type": "rare_state_power",
                        "prevalence": prevalence,
                        "effect_size": effect_size,
                        "repeat": repeat,
                        "n_cells": args.n_cells,
                        "n_genes": args.n_genes,
                        "ari": ari,
                        "nmi": nmi,
                        **rare_metrics,
                        "power_pass": int(
                            (ari >= args.rare_ari_floor)
                            or (rare_metrics["rare_f1"] >= args.rare_f1_floor)
                        ),
                        "rare_ari_floor": args.rare_ari_floor,
                        "rare_f1_floor": args.rare_f1_floor,
                        **fixed,
                        **{
                            key: value
                            for key, value in result.items()
                            if key != "cluster_labels"
                        },
                    }
                )
    return pd.DataFrame(rows)


def summarize(
    null_df: pd.DataFrame, power_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    null_summary = (
        null_df.groupby("null_model", as_index=False)
        .agg(
            n_repeats=("repeat", "nunique"),
            false_signal_rate=("false_signal", "mean"),
            false_call_rate=("false_call", "mean"),
            mean_signal_pcs=("n_signal_pcs", "mean"),
            mean_embedding_pcs=("accepted_embedding_pcs", "mean"),
            no_call_rate=(
                "analysis_status",
                lambda x: float((x == "diagnostic_no_call").mean()),
            ),
            mean_runtime_seconds=("runtime_seconds", "mean"),
        )
        .sort_values("null_model")
    )
    power_summary = (
        power_df.groupby(["prevalence", "effect_size"], as_index=False)
        .agg(
            n_repeats=("repeat", "nunique"),
            power=("power_pass", "mean"),
            mean_ari=("ari", "mean"),
            mean_nmi=("nmi", "mean"),
            mean_rare_precision=("rare_precision", "mean"),
            mean_rare_recall=("rare_recall", "mean"),
            mean_rare_f1=("rare_f1", "mean"),
            mean_fixed30_ari=("fixed_ari", "mean"),
            mean_fixed30_rare_f1=("fixed_rare_f1", "mean"),
            mean_signal_pcs=("n_signal_pcs", "mean"),
            mean_embedding_pcs=("accepted_embedding_pcs", "mean"),
            rare_state_guard_selection_rate=("rare_state_guard_selected", "mean"),
            no_call_rate=(
                "analysis_status",
                lambda x: float((x == "diagnostic_no_call").mean()),
            ),
        )
        .sort_values(["prevalence", "effect_size"])
    )
    return null_summary, power_summary


def build_doc(
    null_summary: pd.DataFrame,
    power_summary: pd.DataFrame,
    paths: dict[str, Path],
    args: argparse.Namespace,
) -> str:
    max_false_signal = (
        float(null_summary["false_signal_rate"].max())
        if not null_summary.empty
        else math.nan
    )
    max_false_call = (
        float(null_summary["false_call_rate"].max())
        if not null_summary.empty
        else math.nan
    )
    rare_floor_rows = power_summary[
        power_summary["prevalence"] <= min(args.prevalence_grid)
    ]
    min_power = (
        float(rare_floor_rows["power"].min()) if not rare_floor_rows.empty else math.nan
    )
    lines = [
        "# Realistic null and rare-state power calibration",
        "",
        "This draft calibration upgrades the synthetic evidence from pure Gaussian-like nulls to count-based scRNA-seq-like nulls.",
        "",
        "## Scope",
        "",
        f"- Cells per run: {args.n_cells}",
        f"- Genes per run: {args.n_genes}",
        f"- Repeats per setting: {args.n_repeats}",
        f"- False signal PC floor: >{args.false_signal_pc_floor} signal PCs",
        f"- Rare-state ARI floor: {args.rare_ari_floor}",
        f"- Rare-state F1 floor: {args.rare_f1_floor}",
        f"- Rare-state guard: {args.rare_state_guard}",
        f"- Rare-state guard fraction window: {args.rare_state_min_fraction} to {args.rare_state_max_fraction}",
        f"- Rare-state guard separation/silhouette floors: {args.rare_state_min_separation} / {args.rare_state_min_silhouette}",
        "",
        "## Outputs",
        "",
    ]
    for label, path in paths.items():
        lines.append(f"- {label}: `{_rel(path)}`")
    lines.extend(
        [
            "",
            "## Null Calibration Summary",
            "",
            "| Null model | Repeats | False signal rate | False call rate | Mean signal PCs | No-call rate |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in null_summary.itertuples(index=False):
        lines.append(
            f"| {row.null_model} | {int(row.n_repeats)} | {row.false_signal_rate:.3f} | {row.false_call_rate:.3f} | {row.mean_signal_pcs:.2f} | {row.no_call_rate:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Rare-State Power Summary",
            "",
            "| Prevalence | Effect size | Repeats | Power | Mean ARI | Rare F1 | fixed 30 PC rare F1 | Guard selected | No-call rate |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in power_summary.itertuples(index=False):
        lines.append(
            f"| {row.prevalence:.3f} | {row.effect_size:.2f} | {int(row.n_repeats)} | {row.power:.3f} | {row.mean_ari:.3f} | {row.mean_rare_f1:.3f} | {row.mean_fixed30_rare_f1:.3f} | {row.rare_state_guard_selection_rate:.3f} | {row.no_call_rate:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            f"- Maximum observed false signal rate in this draft run: {max_false_signal:.3f}.",
            f"- Maximum observed false call rate in this draft run: {max_false_call:.3f}.",
            f"- Minimum power at the lowest prevalence grid in this draft run: {min_power:.3f}.",
            "- These are draft local calibration values. They are useful for detecting failure modes and planning manuscript-grade runs, but final claims require more repeats and confidence intervals.",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument("--n-cells", type=int, default=220)
    parser.add_argument("--n-genes", type=int, default=500)
    parser.add_argument("--n-repeats", type=int, default=4)
    parser.add_argument("--hvg-grid", type=int, nargs="+", default=[150, 300, 500])
    parser.add_argument("--max-pcs", type=int, default=30)
    parser.add_argument("--max-clusters", type=int, default=8)
    parser.add_argument(
        "--pc-rule",
        default="mp_tw",
        choices=["mp", "mp_tw", "permutation", "mp_tw_permutation"],
    )
    parser.add_argument("--n-permutations", type=int, default=0)
    parser.add_argument("--tw-alpha", type=float, default=0.01)
    parser.add_argument("--near-edge-window", type=float, default=1.25)
    parser.add_argument("--embedding-stability-repeats", type=int, default=3)
    parser.add_argument("--embedding-stability-threshold", type=float, default=0.75)
    parser.add_argument(
        "--rare-state-guard",
        default="adaptive_binary_split",
        choices=["off", "adaptive_binary_split"],
    )
    parser.add_argument("--rare-state-min-fraction", type=float, default=0.015)
    parser.add_argument("--rare-state-max-fraction", type=float, default=0.15)
    parser.add_argument("--rare-state-min-cells", type=int, default=4)
    parser.add_argument("--rare-state-min-separation", type=float, default=3.0)
    parser.add_argument("--rare-state-min-silhouette", type=float, default=0.35)
    parser.add_argument("--false-signal-pc-floor", type=int, default=1)
    parser.add_argument("--rare-ari-floor", type=float, default=0.80)
    parser.add_argument("--rare-f1-floor", type=float, default=0.70)
    parser.add_argument(
        "--prevalence-grid", type=float, nargs="+", default=[0.02, 0.04, 0.08]
    )
    parser.add_argument(
        "--effect-size-grid", type=float, nargs="+", default=[2.50, 4.00, 6.00]
    )
    parser.add_argument("--random-state", type=int, default=20260502)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)
    null_df = run_null_calibration(args)
    power_df = run_power_grid(args)
    null_summary, power_summary = summarize(null_df, power_df)

    paths = {
        "null detail": args.outdir / "realistic_null_detail.tsv",
        "null summary": args.outdir / "realistic_null_summary.tsv",
        "power detail": args.outdir / "rare_state_power_detail.tsv",
        "power summary": args.outdir / "rare_state_power_summary.tsv",
    }
    _atomic_write_tsv(null_df, paths["null detail"])
    _atomic_write_tsv(null_summary, paths["null summary"])
    _atomic_write_tsv(power_df, paths["power detail"])
    _atomic_write_tsv(power_summary, paths["power summary"])
    _atomic_write_text(build_doc(null_summary, power_summary, paths, args), DOC)

    for path in paths.values():
        print(_rel(path))
    print(_rel(DOC))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
